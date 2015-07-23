cmake_minimum_required(VERSION 2.8.4)
project(sdCard)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

set(SOURCE_FILES
    sd_reader.cpp)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "~/Desktop/ABOVE_TCP/sdCard")
add_executable(sdCard ${SOURCE_FILES})