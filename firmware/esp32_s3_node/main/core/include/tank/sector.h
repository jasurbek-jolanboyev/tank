#pragma once
#include <cstddef>
#include <optional>
#include <string_view>

namespace tank {
enum class SectorId { Top1, Top2, Top3, Front1, Front2, Rear1, Rear2, Left1, Left2, Right1, Right2 };
constexpr std::size_t kSectorCount = 11;
std::string_view sectorName(SectorId sector);
std::optional<SectorId> parseSector(std::string_view name);
}  // namespace tank

