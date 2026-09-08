#include <cassert>
#include <iostream>
#include "tank/indicator_manager.h"
#include "tank/sector.h"
#include "tank/tf02_frame_parser.h"

int main() {
  using namespace tank;
  for (auto name : {"TOP_1","TOP_2","TOP_3","FRONT_1","FRONT_2","REAR_1","REAR_2","LEFT_1","LEFT_2","RIGHT_1","RIGHT_2"}) {
    auto sector = parseSector(name); assert(sector); assert(sectorName(*sector) == name);
  }
  TemporalValidator validator;
  BoundingBox box{.x=.1f,.y=.1f,.width=.2f,.height=.2f};
  assert(validator.observe({1,ObjectClass::Drone,.9f,box,0,false},0) == AlertState::DroneCandidate);
  assert(validator.observe({1,ObjectClass::Drone,.9f,box,150,false},0) == AlertState::DroneCandidate);
  assert(validator.observe({1,ObjectClass::Drone,.9f,box,300,false},0) == AlertState::DroneConfirmed);
  IndicatorManager lights;
  assert(lights.update(AlertState::DroneConfirmed,true,30,true,300,300)==IndicatorState::White);
  assert(lights.update(AlertState::DroneConfirmed,true,19,true,400,400)==IndicatorState::Red);
  assert(lights.update(AlertState::DroneConfirmed,true,21,true,500,500)==IndicatorState::Red);
  assert(lights.update(AlertState::DroneConfirmed,true,23,true,600,600)==IndicatorState::White);
  assert(lights.update(AlertState::TrackLost,false,0,false,600,3000)==IndicatorState::Off);
  Tf02FrameParser parser; Tf02Frame frame;
  unsigned char tf02[]{0x59,0x59,0x3A,0x07,0x34,0x12,0x00,0x08,0x41};
  bool parsed=false; for (auto byte : tf02) parsed = parser.feed(byte,frame) || parsed;
  assert(parsed); assert(frame.distanceCentimeters==1850); assert(frame.signalStrength==0x1234);
  tf02[8]=0; parsed=false; for (auto byte : tf02) parsed = parser.feed(byte,frame) || parsed;
  assert(!parsed); assert(parser.errorCount()==1);
  std::cout << "core tests passed\n";
}
