# Install script for directory: /home/n71743ev/DUMUX/dumux/Mixing-in-UHS/dumux/material/binarycoefficients

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/usr/local")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "Release")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Install shared libraries without execute permission?
if(NOT DEFINED CMAKE_INSTALL_SO_NO_EXE)
  set(CMAKE_INSTALL_SO_NO_EXE "1")
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

# Set default install directory permissions.
if(NOT DEFINED CMAKE_OBJDUMP)
  set(CMAKE_OBJDUMP "/usr/bin/objdump")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/dumux/material/binarycoefficients" TYPE FILE FILES
    "/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/dumux/material/binarycoefficients/co2_n2.hh"
    "/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/dumux/material/binarycoefficients/h2o_n2.hh"
    "/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/dumux/material/binarycoefficients/h2_ch4.hh"
    "/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/dumux/material/binarycoefficients/h2_co2.hh"
    "/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/dumux/material/binarycoefficients/ch4_ch4.hh"
    "/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/dumux/material/binarycoefficients/ch4_co2.hh"
    "/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/dumux/material/binarycoefficients/h2_n2.hh"
    "/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/dumux/material/binarycoefficients/h2o_ch4.hh"
    "/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/dumux/material/binarycoefficients/ch4_n2.hh"
    "/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/dumux/material/binarycoefficients/h2o_co2.hh"
    "/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/dumux/material/binarycoefficients/h2o_h2.hh"
    "/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/dumux/material/binarycoefficients/h2_co2_not.hh"
    )
endif()

