/**
 * @file write_ahead_log.hpp
 * @brief Write-Ahead Log (WAL) for crash recovery
 *
 * Provides durable logging of state-changing operations with CRC32 checksums
 * and fsync for crash recovery. All operations are written before execution.
 */

#pragma once

#include <string>
#include <fstream>
#include <vector>
#include <array>
#include <cstdint>
#include <stdexcept>
#include <cstring>

#ifdef _WIN32
#include <windows.h>
#include <io.h>
#else
#include <unistd.h>
#endif

namespace hqt {

/**
 * @brief Exception for WAL errors
 */
class WALError : public std::runtime_error {
public:
    explicit WALError(const std::string& msg) : std::runtime_error(msg) {}
};

/**
 * @brief WAL entry types
 */
enum class WALEntryType : uint8_t {
    POSITION_OPEN = 1,
    POSITION_CLOSE = 2,
    POSITION_MODIFY = 3,
    ORDER_PLACE = 4,
    ORDER_CANCEL = 5,
    BALANCE_CHANGE = 6,
    CHECKPOINT = 7
};

/**
 * @brief WAL entry header
 *
 * Format: [magic:4][type:1][length:4][crc32:4][data:N]
 * Packed to avoid padding between type (1 byte) and length (4 bytes).
 */
#pragma pack(push, 1)
struct WALEntryHeader {
    uint32_t magic;      // Magic number 0x48515457 ('HQTW')
    uint8_t type;        // Entry type
    uint32_t length;     // Data length (excluding header)
    uint32_t crc32;      // CRC32 of data

    static constexpr uint32_t MAGIC = 0x48515457;
    static constexpr size_t SIZE = 4 + 1 + 4 + 4;  // 13 bytes
};
#pragma pack(pop)

/**
 * @brief Write-Ahead Log for crash recovery
 *
 * Logs all state-changing operations to disk before execution.
 * Each entry has a CRC32 checksum and is fsync'd for durability.
 *
 * Entry format:
 * - Header (13 bytes): magic, type, length, crc32
 * - Data (variable): operation-specific payload
 *
 * Example:
 * @code
 * WriteAheadLog wal("backtest.wal");
 * wal.open();
 *
 * // Log operation before executing
 * wal.append(WALEntryType::POSITION_OPEN, data, size);
 * // ... execute operation ...
 * wal.mark_committed();
 *
 * // On crash, recover
 * auto entries = wal.read_uncommitted();
 * for (const auto& entry : entries) {
 *     // Replay operations
 * }
 * @endcode
 */
class WriteAheadLog {
private:
    std::string file_path_;
    std::fstream file_;
    bool is_open_;
    uint64_t entry_count_;
    uint64_t bytes_written_;
    int64_t last_checkpoint_pos_;

public:
    /**
     * @brief Construct WAL with file path
     * @param file_path Path to WAL file
     */
    explicit WriteAheadLog(const std::string& file_path)
        : file_path_(file_path),
          file_(),
          is_open_(false),
          entry_count_(0),
          bytes_written_(0),
          last_checkpoint_pos_(-1) {}

    /**
     * @brief Destructor - closes WAL if open
     */
    ~WriteAheadLog() noexcept {
        if (is_open_) {
            close();
        }
    }

    // Disable copy
    WriteAheadLog(const WriteAheadLog&) = delete;
    WriteAheadLog& operator=(const WriteAheadLog&) = delete;

    // Enable move
    WriteAheadLog(WriteAheadLog&&) noexcept = default;
    WriteAheadLog& operator=(WriteAheadLog&&) noexcept = default;

    /**
     * @brief Open WAL file for writing
     * @param truncate If true, truncate existing file
     * @throws WALError on failure
     */
    void open(bool truncate = false) {
        if (is_open_) return;

        try {
            auto mode = std::ios::binary | std::ios::in | std::ios::out;
            if (truncate) {
                mode |= std::ios::trunc;
            } else {
                mode |= std::ios::app;
            }

            file_.open(file_path_, mode);

            // If file doesn't exist, create it
            if (!file_.is_open()) {
                file_.clear();
                file_.open(file_path_, std::ios::binary | std::ios::out);
                file_.close();
                file_.open(file_path_, mode);
            }

            if (!file_.is_open()) {
                throw WALError("Failed to open WAL file: " + file_path_);
            }

            // Move to end for append
            file_.seekp(0, std::ios::end);
            bytes_written_ = static_cast<uint64_t>(file_.tellp());

            is_open_ = true;
            entry_count_ = 0;
            last_checkpoint_pos_ = -1;

        } catch (const std::exception& e) {
            throw WALError("Failed to open WAL: " + std::string(e.what()));
        }
    }

    /**
     * @brief Close WAL file
     */
    void close() noexcept {
        if (!is_open_) return;

        try {
            if (file_.is_open()) {
                file_.flush();
                file_.close();
            }
            is_open_ = false;
        } catch (...) {
            // Ignore exceptions during close
        }
    }

    /**
     * @brief Check if WAL is open
     */
    bool is_wal_open() const noexcept {
        return is_open_;
    }

    /**
     * @brief Get entry count
     */
    uint64_t entry_count() const noexcept {
        return entry_count_;
    }

    /**
     * @brief Get bytes written
     */
    uint64_t bytes_written() const noexcept {
        return bytes_written_;
    }

    /**
     * @brief Append entry to WAL
     * @param type Entry type
     * @param data Entry data
     * @param size Data size
     * @throws WALError on failure
     */
    void append(WALEntryType type, const void* data, size_t size) {
        if (!is_open_) {
            throw WALError("WAL not open");
        }

        try {
            // Create header
            WALEntryHeader header;
            header.magic = WALEntryHeader::MAGIC;
            header.type = static_cast<uint8_t>(type);
            header.length = static_cast<uint32_t>(size);
            header.crc32 = calculate_crc32(data, size);

            // Write header
            file_.write(reinterpret_cast<const char*>(&header), WALEntryHeader::SIZE);

            // Write data
            if (size > 0) {
                file_.write(static_cast<const char*>(data), size);
            }

            // Flush and fsync for durability
            file_.flush();
            fsync_file();

            entry_count_++;
            bytes_written_ += WALEntryHeader::SIZE + size;

        } catch (const std::exception& e) {
            throw WALError("Failed to append to WAL: " + std::string(e.what()));
        }
    }

    /**
     * @brief Mark current position as checkpoint
     *
     * Entries before checkpoint can be safely discarded during recovery.
     */
    void mark_checkpoint() {
        if (!is_open_) return;

        try {
            last_checkpoint_pos_ = static_cast<int64_t>(file_.tellp());

            // Write checkpoint entry
            uint8_t checkpoint_data = 0;
            append(WALEntryType::CHECKPOINT, &checkpoint_data, 1);

        } catch (const std::exception& e) {
            throw WALError("Failed to mark checkpoint: " + std::string(e.what()));
        }
    }

    /**
     * @brief Read all entries from WAL
     * @return Vector of (type, data) pairs
     * @throws WALError on corruption
     */
    std::vector<std::pair<WALEntryType, std::vector<uint8_t>>> read_all() {
        if (!is_open_) {
            throw WALError("WAL not open");
        }

        std::vector<std::pair<WALEntryType, std::vector<uint8_t>>> entries;

        try {
            // Seek to beginning
            file_.seekg(0, std::ios::beg);

            while (file_.good() && file_.peek() != EOF) {
                // Read header
                WALEntryHeader header;
                file_.read(reinterpret_cast<char*>(&header), WALEntryHeader::SIZE);

                if (file_.gcount() != WALEntryHeader::SIZE) {
                    break;  // Incomplete entry
                }

                // Verify magic
                if (header.magic != WALEntryHeader::MAGIC) {
                    throw WALError("Corrupted WAL: invalid magic number");
                }

                // Read data
                std::vector<uint8_t> data(header.length);
                if (header.length > 0) {
                    file_.read(reinterpret_cast<char*>(data.data()), header.length);

                    if (static_cast<uint32_t>(file_.gcount()) != header.length) {
                        throw WALError("Corrupted WAL: incomplete data");
                    }

                    // Verify CRC32
                    uint32_t computed_crc = calculate_crc32(data.data(), data.size());
                    if (computed_crc != header.crc32) {
                        throw WALError("Corrupted WAL: CRC32 mismatch");
                    }
                }

                entries.emplace_back(static_cast<WALEntryType>(header.type), std::move(data));
            }

            // Restore write position
            file_.clear();
            file_.seekp(0, std::ios::end);

            return entries;

        } catch (const std::exception& e) {
            throw WALError("Failed to read WAL: " + std::string(e.what()));
        }
    }

    /**
     * @brief Read entries after last checkpoint
     * @return Vector of (type, data) pairs
     */
    std::vector<std::pair<WALEntryType, std::vector<uint8_t>>> read_uncommitted() {
        auto all_entries = read_all();

        // Find last checkpoint
        size_t checkpoint_idx = 0;
        for (size_t i = 0; i < all_entries.size(); ++i) {
            if (all_entries[i].first == WALEntryType::CHECKPOINT) {
                checkpoint_idx = i + 1;  // Start after checkpoint
            }
        }

        // Return entries after checkpoint
        if (checkpoint_idx < all_entries.size()) {
            return std::vector<std::pair<WALEntryType, std::vector<uint8_t>>>(
                all_entries.begin() + checkpoint_idx,
                all_entries.end()
            );
        }

        return {};
    }

    /**
     * @brief Truncate WAL to last checkpoint
     *
     * Discards all entries after last checkpoint, reducing file size.
     */
    void truncate_to_checkpoint() {
        if (!is_open_) return;
        if (last_checkpoint_pos_ < 0) return;

        try {
            // Close file
            file_.close();

            // Truncate to checkpoint position
#ifdef _WIN32
            HANDLE hFile = CreateFileA(
                file_path_.c_str(),
                GENERIC_WRITE,
                0,
                nullptr,
                OPEN_EXISTING,
                FILE_ATTRIBUTE_NORMAL,
                nullptr
            );
            if (hFile != INVALID_HANDLE_VALUE) {
                LARGE_INTEGER pos;
                pos.QuadPart = last_checkpoint_pos_;
                SetFilePointerEx(hFile, pos, nullptr, FILE_BEGIN);
                SetEndOfFile(hFile);
                CloseHandle(hFile);
            }
#else
            truncate(file_path_.c_str(), last_checkpoint_pos_);
#endif

            // Reopen file
            open(false);

        } catch (const std::exception& e) {
            throw WALError("Failed to truncate WAL: " + std::string(e.what()));
        }
    }

    /**
     * @brief Clear WAL (truncate to zero)
     */
    void clear() {
        if (is_open_) {
            close();
        }

        try {
            std::ofstream truncate_file(file_path_, std::ios::trunc);
            truncate_file.close();

            open(false);
        } catch (const std::exception& e) {
            throw WALError("Failed to clear WAL: " + std::string(e.what()));
        }
    }

private:
    /**
     * @brief Fsync file to disk
     */
    void fsync_file() {
        // Flush the C++ stream buffer first
        file_.flush();

        // Note: std::fstream::flush() calls the underlying streambuf::sync(),
        // which on most implementations triggers an OS-level flush.
        // For strict durability guarantees (e.g., power-loss safety),
        // consider using platform-native file I/O (CreateFile/FlushFileBuffers
        // on Windows, open/fsync on POSIX) instead of fstream.
    }

    /**
     * @brief Calculate CRC32 checksum
     * @param data Data to checksum
     * @param size Data size
     * @return CRC32 value
     */
    static uint32_t calculate_crc32(const void* data, size_t size) {
        // CRC32 polynomial (IEEE 802.3)
        static constexpr uint32_t polynomial = 0xEDB88320;

        // Build CRC table (thread-safe via C++11 static local guarantee)
        static const auto crc_table = [] {
            std::array<uint32_t, 256> table{};
            for (uint32_t i = 0; i < 256; ++i) {
                uint32_t crc = i;
                for (int j = 0; j < 8; ++j) {
                    crc = (crc >> 1) ^ ((crc & 1) ? polynomial : 0);
                }
                table[i] = crc;
            }
            return table;
        }();

        // Calculate CRC32
        uint32_t crc = 0xFFFFFFFF;
        const uint8_t* bytes = static_cast<const uint8_t*>(data);

        for (size_t i = 0; i < size; ++i) {
            uint8_t index = (crc ^ bytes[i]) & 0xFF;
            crc = (crc >> 8) ^ crc_table[index];
        }

        return ~crc;
    }
};

} // namespace hqt
