cmake_minimum_required(VERSION 2.8.4)
project(ABOVE_TCP)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

set(SOURCE_FILES
    sdCard/sd_reader.cpp)

add_executable(ABOVE_TCP ${SOURCE_FILES})