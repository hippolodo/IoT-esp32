#pragma once
#include <stdint.h>

struct AlertCounter {
  uint32_t count;
  bool active;
};

// Call once per sensor sample: every valid reading above the threshold adds one.
// Keep the active field so existing NVS records remain readable.
constexpr AlertCounter advanceAlertCounter(AlertCounter previous, bool valid, bool exceeded) {
  return !valid ? previous : AlertCounter{
    previous.count + ((exceeded && previous.count < UINT32_MAX) ? 1u : 0u),
    exceeded
  };
}
