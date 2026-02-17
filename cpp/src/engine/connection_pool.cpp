/**
 * @file connection_pool.cpp
 * @brief Configurable connection-pool concurrency primitive.
 */

#include "util/connection_pool.hpp"

namespace hqt::util {

ConnectionPool::Lease::Lease(ConnectionPool* owner, const bool overflow) noexcept
    : owner_(owner), overflow_(overflow) {}

ConnectionPool::Lease::Lease(Lease&& other) noexcept
    : owner_(other.owner_), overflow_(other.overflow_) {
    other.owner_ = nullptr;
    other.overflow_ = false;
}

ConnectionPool::Lease& ConnectionPool::Lease::operator=(Lease&& other) noexcept {
    if (this == &other) {
        return *this;
    }
    reset();
    owner_ = other.owner_;
    overflow_ = other.overflow_;
    other.owner_ = nullptr;
    other.overflow_ = false;
    return *this;
}

ConnectionPool::Lease::~Lease() {
    reset();
}

bool ConnectionPool::Lease::valid() const noexcept {
    return owner_ != nullptr;
}

bool ConnectionPool::Lease::is_overflow() const noexcept {
    return overflow_;
}

void ConnectionPool::Lease::reset() noexcept {
    if (owner_ == nullptr) {
        return;
    }
    owner_->release(overflow_);
    owner_ = nullptr;
    overflow_ = false;
}

ConnectionPool::ConnectionPool(ConnectionPoolConfig config)
    : config_(config) {}

std::optional<ConnectionPool::Lease> ConnectionPool::acquire() {
    std::unique_lock<std::mutex> lock(mutex_);
    const std::size_t max_total = config_.pool_size + config_.max_overflow;

    const bool ready = cv_.wait_for(lock, config_.acquire_timeout, [&]() {
        return (base_in_use_ + overflow_in_use_) < max_total;
    });

    if (!ready) {
        return std::nullopt;
    }

    bool overflow = false;
    if (base_in_use_ < config_.pool_size) {
        ++base_in_use_;
    } else {
        ++overflow_in_use_;
        overflow = true;
    }

    return Lease(this, overflow);
}

std::size_t ConnectionPool::in_use() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return base_in_use_ + overflow_in_use_;
}

std::size_t ConnectionPool::base_in_use() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return base_in_use_;
}

std::size_t ConnectionPool::overflow_in_use() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return overflow_in_use_;
}

std::size_t ConnectionPool::capacity() const {
    return config_.pool_size + config_.max_overflow;
}

ConnectionPoolConfig ConnectionPool::config() const {
    return config_;
}

void ConnectionPool::release(const bool overflow) {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        if (overflow) {
            if (overflow_in_use_ > 0) {
                --overflow_in_use_;
            }
        } else {
            if (base_in_use_ > 0) {
                --base_in_use_;
            }
        }
    }
    cv_.notify_one();
}

}  // namespace hqt::util

