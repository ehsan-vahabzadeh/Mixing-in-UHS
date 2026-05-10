if(NOT MIXING-IN-UHS_FOUND)
# Whether this module is installed or not
set(MIXING-IN-UHS_INSTALLED ON)

# Settings specific to the module

# Package initialization

####### Expanded from @PACKAGE_INIT@ by configure_package_config_file() #######
####### Any changes to this file will be overwritten by the next CMake run ####
####### The input file was MIXING-IN-UHS-config.cmake.in                            ########

get_filename_component(PACKAGE_PREFIX_DIR "${CMAKE_CURRENT_LIST_DIR}/../../../" ABSOLUTE)

macro(set_and_check _var _file)
  set(${_var} "${_file}")
  if(NOT EXISTS "${_file}")
    message(FATAL_ERROR "File or directory ${_file} referenced by variable ${_var} does not exist !")
  endif()
endmacro()

macro(check_required_components _NAME)
  foreach(comp ${${_NAME}_FIND_COMPONENTS})
    if(NOT ${_NAME}_${comp}_FOUND)
      if(${_NAME}_FIND_REQUIRED_${comp})
        set(${_NAME}_FOUND FALSE)
      endif()
    endif()
  endforeach()
endmacro()

####################################################################################

#report other information
set_and_check(MIXING-IN-UHS_PREFIX "${PACKAGE_PREFIX_DIR}")
set_and_check(MIXING-IN-UHS_INCLUDE_DIRS "${PACKAGE_PREFIX_DIR}/include")
set(MIXING-IN-UHS_CMAKE_CONFIG_VERSION "2.10")
set(MIXING-IN-UHS_CXX_FLAGS "")
set(MIXING-IN-UHS_CXX_FLAGS_DEBUG "-O0 -g -ggdb -Wall -Wextra -Wno-unused-parameter -Wno-sign-compare -DDUNE_CHECK_BOUNDS=ON")
set(MIXING-IN-UHS_CXX_FLAGS_MINSIZEREL "-Os -DNDEBUG")
set(MIXING-IN-UHS_CXX_FLAGS_RELEASE " -fdiagnostics-color=always -fno-strict-aliasing -fstrict-overflow -fno-finite-math-only -DNDEBUG=1 -O3 -march=native -funroll-loops -g0 -Wall -Wunused -Wmissing-include-dirs -Wcast-align -Wno-missing-braces -Wmissing-field-initializers -Wno-sign-compare")
set(MIXING-IN-UHS_CXX_FLAGS_RELWITHDEBINFO " -fdiagnostics-color=always -fno-strict-aliasing -fstrict-overflow -fno-finite-math-only -DNDEBUG=1 -O3 -march=native -funroll-loops -g0 -Wall -Wunused -Wmissing-include-dirs -Wcast-align -Wno-missing-braces -Wmissing-field-initializers -Wno-sign-compare -g -ggdb -Wall")
set(MIXING-IN-UHS_DEPENDS "dumux")
set(MIXING-IN-UHS_SUGGESTS "")
set(MIXING-IN-UHS_MODULE_PATH "${PACKAGE_PREFIX_DIR}/share/dune/cmake/modules")
set(MIXING-IN-UHS_PYTHON_WHEELHOUSE "${PACKAGE_PREFIX_DIR}/share/dune/wheelhouse")
set(MIXING-IN-UHS_LIBRARIES "")
set(MIXING-IN-UHS_HASPYTHON 0)
set(MIXING-IN-UHS_PYTHONREQUIRES "")

# Resolve dune dependencies
include(CMakeFindDependencyMacro)
macro(find_and_check_dune_dependency module version)
  find_dependency(${module})
  list(PREPEND CMAKE_MODULE_PATH "${dune-common_MODULE_PATH}")
  include(DuneModuleDependencies)
  list(POP_FRONT CMAKE_MODULE_PATH)
  if(dune-common_VERSION VERSION_GREATER_EQUAL "2.10")
    dune_check_module_version(${module} QUIET REQUIRED VERSION "${version}")
  endif()
endmacro()

find_and_check_dune_dependency(dumux " ")

# Set up DUNE_LIBS, DUNE_FOUND_DEPENDENCIES, DUNE_*_FOUND, and HAVE_* variables
if(MIXING-IN-UHS_LIBRARIES)
  message(STATUS "Setting MIXING-IN-UHS_LIBRARIES=${MIXING-IN-UHS_LIBRARIES}")
  list(PREPEND DUNE_LIBS ${MIXING-IN-UHS_LIBRARIES})
endif()
list(APPEND DUNE_FOUND_DEPENDENCIES MIXING-IN-UHS)
set(DUNE_MIXING-IN-UHS_FOUND TRUE)
set(HAVE_MIXING_IN_UHS TRUE)

# Lines that are set by the CMake build system via the variable DUNE_CUSTOM_PKG_CONFIG_SECTION


# If this file is found in a super build that includes MIXING-IN-UHS, the 
# `MIXING-IN-UHS-targets.cmake`-file has not yet been generated. This variable
# determines whether the configuration of MIXING-IN-UHS has been completed.
get_property(MIXING-IN-UHS_IN_CONFIG_MODE GLOBAL PROPERTY MIXING-IN-UHS_LIBRARIES DEFINED)

#import the target
if(MIXING-IN-UHS_LIBRARIES AND NOT MIXING-IN-UHS_IN_CONFIG_MODE)
  get_filename_component(_dir "${CMAKE_CURRENT_LIST_FILE}" PATH)
  include("${_dir}/MIXING-IN-UHS-targets.cmake")
endif()

endif()
