#pragma once
// Point SNTP at whatever gateway DHCP handed us.
//
// The node must not reach the internet, so a public NTP pool is not an option,
// and hardcoding one LAN's router address makes the config unusable on any
// other network. The default gateway is the one address that is always correct
// per-network and needs no configuration.
#include "esp_netif.h"
#include "esp_sntp.h"
#include "esphome/core/log.h"

namespace homey_ntp {

/// Repoint SNTP server 0 at the DHCP-supplied default gateway.
///
/// Called on a retry interval, not once at boot: on_boot fires before the DHCP
/// lease exists, so there is no gateway to read yet. Returns true once applied,
/// after which it is a no-op.
inline bool use_default_gateway() {
  static bool applied = false;
  if (applied)
    return true;
  esp_netif_t *netif = esp_netif_get_default_netif();
  esp_netif_ip_info_t info{};
  if (netif == nullptr || esp_netif_get_ip_info(netif, &info) != ESP_OK || info.gw.addr == 0) {
    ESP_LOGD("ntp", "no default gateway yet; will retry");
    return false;
  }
  static char gateway[16];
  snprintf(gateway, sizeof(gateway), IPSTR, IP2STR(&info.gw));
  ESP_LOGI("ntp", "using default gateway %s as NTP server", gateway);
  if (esp_sntp_enabled())
    esp_sntp_stop();
  esp_sntp_setservername(0, gateway);
  esp_sntp_init();
  applied = true;
  return true;
}

}  // namespace homey_ntp
