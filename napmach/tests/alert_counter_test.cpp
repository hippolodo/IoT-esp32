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
// Restoring the NVS state on reboot must not start the same episode again.
constexpr AlertCounter restored{second.count, second.active};
constexpr auto afterReset = advanceAlertCounter(restored, true, true);
constexpr auto rearmed = advanceAlertCounter(afterReset, true, false);
constexpr auto afterResetNextEpisode = advanceAlertCounter(rearmed, true, true);
static_assert(afterReset.count == 2, "Reset while above threshold must preserve one episode");
static_assert(afterResetNextEpisode.count == 3, "A later episode continues the saved total");
static_assert(advanceAlertCounter(initial, true, true).count == 1, "A separate LED starts independently");
static_assert(second.count == 2, "Updating a separate counter must not change other LEDs");
static_assert(advanceAlertCounter({UINT32_MAX, false}, true, true).count == UINT32_MAX,
              "Counter must saturate instead of wrapping to zero");
