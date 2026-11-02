#include "AlertCounter.h"

constexpr AlertCounter initial{0, false};
constexpr float threshold = 30;
constexpr auto below = advanceAlertCounter(initial, true, 29 > threshold);
constexpr auto equal = advanceAlertCounter(below, true, 30 > threshold);
constexpr auto first35 = advanceAlertCounter(equal, true, 35 > threshold);
constexpr auto second35 = advanceAlertCounter(first35, true, 35 > threshold);
constexpr auto third35 = advanceAlertCounter(second35, true, 35 > threshold);
static_assert(below.count == 0 && equal.count == 0, "At or below threshold must not add alerts");
static_assert(first35.count == 1, "First sample at 35 above threshold 30 adds one alert");
static_assert(second35.count == 2, "An identical second sample at 35 must add another alert");
static_assert(third35.count == 3 && third35.active, "Each fresh high sample adds one alert");

constexpr auto missing = advanceAlertCounter(third35, false, true);
constexpr auto recovered35 = advanceAlertCounter(missing, true, 35 > threshold);
constexpr auto normal = advanceAlertCounter(recovered35, true, false);
constexpr auto next35 = advanceAlertCounter(normal, true, 35 > threshold);
static_assert(missing.count == 3, "Invalid samples must not add alerts");
static_assert(recovered35.count == 4, "A valid high sample after recovery adds one alert");
static_assert(normal.count == 4 && !normal.active, "Normal samples preserve the total");
static_assert(next35.count == 5, "A later high sample continues the total");

// NVS restores the previous total; the first new high sample after reboot counts.
constexpr AlertCounter restored{next35.count, next35.active};
constexpr auto afterReset = advanceAlertCounter(restored, true, true);
static_assert(afterReset.count == 6, "New high readings count even if NVS active was true");
static_assert(advanceAlertCounter(initial, true, true).count == 1, "Each LED counts independently");
static_assert(third35.count == 3, "Updating another counter does not affect this LED");
static_assert(advanceAlertCounter({UINT32_MAX, true}, true, true).count == UINT32_MAX,
              "Counter must saturate instead of wrapping to zero");
