#include "AlertCounter.h"

constexpr AlertCounter initial{0, false};
constexpr auto normal = advanceAlertCounter(initial, true, false);
constexpr auto first = advanceAlertCounter(normal, true, true);
constexpr auto ongoing = advanceAlertCounter(first, true, true);
constexpr auto missing = advanceAlertCounter(ongoing, false, false);
constexpr auto recovered = advanceAlertCounter(missing, true, true);
constexpr auto equalOrBelow = advanceAlertCounter(recovered, true, false);
constexpr auto second = advanceAlertCounter(equalOrBelow, true, true);
static_assert(normal.count == 0, "Normal readings must not trigger alerts");
static_assert(first.count == 1 && first.active, "First high reading starts one episode");
static_assert(ongoing.count == 1, "Repeated samples and blink cycles must not add alerts");
static_assert(missing.count == 1 && missing.active, "Missing data must preserve the episode");
static_assert(recovered.count == 1, "Recovery while still high must not retrigger");
static_assert(equalOrBelow.count == 1 && !equalOrBelow.active, "At or below threshold rearms");
static_assert(second.count == 2 && second.active, "A new excursion adds one alert");
static_assert(advanceAlertCounter(initial, true, true).count == 1, "A separate LED starts independently");
static_assert(second.count == 2, "Updating a separate counter must not change other LEDs");
static_assert(advanceAlertCounter({UINT32_MAX, false}, true, true).count == UINT32_MAX,
              "Counter must saturate instead of wrapping to zero");
