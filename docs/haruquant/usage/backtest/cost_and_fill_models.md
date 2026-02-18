# Fill Simulator and Transaction Cost Models (IP-39)

IP-39 is implemented in C++ via `CostsEngine` and model interfaces under `cpp/include/costs/`.

## Components

- `cpp/include/costs/costs_engine.hpp`
- `cpp/include/costs/slippage_model.hpp`
- `cpp/include/costs/commission_model.hpp`
- `cpp/include/costs/swap_model.hpp`
- `cpp/include/costs/spread_model.hpp`

## Covered Behavior

- Fill simulation:
  - market/limit/stop/stop-limit order evaluation
  - SL/TP exit evaluation
  - gap handling (fills at market gap price, not requested stop/limit level when crossed)
- Transaction costs:
  - slippage
  - spread cost
  - commission (fixed per lot, fixed per trade, percentage, tiered)
  - swap/financing
- Determinism:
  - seeded RNG in `CostsEngine` constructor
  - deterministic behavior when same seed and same market inputs are used

## Minimal C++ Example

```cpp
#include "costs/costs_engine.hpp"
#include "costs/slippage_model.hpp"
#include "costs/commission_model.hpp"
#include "costs/swap_model.hpp"
#include "costs/spread_model.hpp"

using namespace hqt;

auto engine = CostsEngine(
    std::make_unique<FixedSlippage>(2),
    std::make_unique<FixedPerLot>(7'000'000),  // $7/lot in fixed-point
    std::make_unique<StandardSwap>(-0.5, 0.3, SwapType::POINTS),
    std::make_unique<FixedSpread>(15),
    42  // deterministic seed
);

Tick tick{1'000'000, 1, 1'100'000, 1'100'020, 1'000'000, 1'000'000, 20};
SymbolInfo symbol;
symbol.SetDigits(5);
symbol.SetPoint(0.00001);
symbol.SetContractSize(100000.0);

auto fill = engine.execute_market_order(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 1.0, tick, symbol);
```

## Validation

- `cpp/tests/test_costs_engine.cpp`
  - order trigger and fill behavior
  - gap scenario behavior
  - commission/swap/spread/slippage models
  - deterministic seeded execution
