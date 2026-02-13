/**
 * @file infrastructure.cpp
 * @brief Unified engine infrastructure module.
 *
 * Event loop and global clock are header-implemented today. WAL and
 * broadcaster remain available via their headers but are not pulled into this
 * target's compilation unit to avoid heavy dependencies in hqt_core.
 */

#include "engine/event.hpp"
#include "engine/event_loop.hpp"
#include "engine/global_clock.hpp"

namespace hqt::engine {

[[maybe_unused]] static constexpr int kInfrastructureModuleScaffold = 1;

}  // namespace hqt::engine
