#include "tank/sector.h"
#include <array>

namespace tank {
namespace {
using Entry = std::pair<SectorId, std::string_view>;
constexpr std::array<Entry, kSectorCount> sectors{{
 {SectorId::Top1,"TOP_1"},{SectorId::Top2,"TOP_2"},{SectorId::Top3,"TOP_3"},
 {SectorId::Front1,"FRONT_1"},{SectorId::Front2,"FRONT_2"},
 {SectorId::Rear1,"REAR_1"},{SectorId::Rear2,"REAR_2"},
 {SectorId::Left1,"LEFT_1"},{SectorId::Left2,"LEFT_2"},
 {SectorId::Right1,"RIGHT_1"},{SectorId::Right2,"RIGHT_2"}}};
}
std::string_view sectorName(SectorId sector) {
  for (const auto& entry : sectors) if (entry.first == sector) return entry.second;
  return "UNKNOWN";
}
std::optional<SectorId> parseSector(std::string_view name) {
  for (const auto& entry : sectors) if (entry.second == name) return entry.first;
  return std::nullopt;
}
}  // namespace tank

