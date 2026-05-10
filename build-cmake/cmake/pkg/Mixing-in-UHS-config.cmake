if(NOT Mixing-in-UHS_FOUND)
# Whether this module is installed or not
set(Mixing-in-UHS_INSTALLED ON)

# Settings specific to the module

# Package initialization

####### Expanded from @PACKAGE_INIT@ by configure_package_config_file() #######
####### Any changes to this file will be overwritten by the next CMake run ####
####### The input file was Mixing-in-UHS-config.cmake.in                            ########

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
set_and_check(Mixing-in-UHS_PREFIX "${PACKAGE_PREFIX_DIR}")
set_and_check(Mixing-in-UHS_INCLUDE_DIRS "${PACKAGE_PREFIX_DIR}/include")
set(Mixing-in-UHS_CMAKE_CONFIG_VERSION "2.10")
set(Mixing-in-UHS_CXX_FLAGS "")
set(Mixing-in-UHS_CXX_FLAGS_DEBUG "-O0 -g -ggdb -Wall -Wextra -Wno-unused-parameter -Wno-sign-compare -DDUNE_CHECK_BOUNDS=ON")
set(Mixing-in-UHS_CXX_FLAGS_MINSIZEREL "-Os -DNDEBUG")
set(Mixing-in-UHS_CXX_FLAGS_RELEASE " -fdiagnostics-color=always -fno-strict-aliasing -fstrict-overflow -fno-finite-math-only -DNDEBUG=1 -O3 -march=native -funroll-loops -g0 -Wall -Wunused -Wmissing-include-dirs -Wcast-align -Wno-missing-braces -Wmissing-field-initializers -Wno-sign-compare")
set(Mixing-in-UHS_CXX_FLAGS_RELWITHDEBINFO " -fdiagnostics-color=always -fno-strict-aliasing -fstrict-overflow -fno-finite-math-only -DNDEBUG=1 -O3 -march=native -funroll-loops -g0 -Wall -Wunused -Wmissing-include-dirs -Wcast-align -Wno-missing-braces -Wmissing-field-initializers -Wno-sign-compare -g -ggdb -Wall")
set(Mixing-in-UHS_DEPENDS "dumux")
set(Mixing-in-UHS_SUGGESTS "")
set(Mixing-in-UHS_MODULE_PATH "${PACKAGE_PREFIX_DIR}/share/dune/cmake/modules")
set(Mixing-in-UHS_PYTHON_WHEELHOUSE "${PACKAGE_PREFIX_DIR}/share/dune/wheelhouse")
set(Mixing-in-UHS_LIBRARIES "")
set(Mixing-in-UHS_HASPYTHON 0)
set(Mixing-in-UHS_PYTHONREQUIRES "")

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
if(Mixing-in-UHS_LIBRARIES)
  message(STATUS "Setting Mixing-in-UHS_LIBRARIES=${Mixing-in-UHS_LIBRARIES}")
  list(PREPEND DUNE_LIBS ${Mixing-in-UHS_LIBRARIES})
endif()
list(APPEND DUNE_FOUND_DEPENDENCIES Mixing-in-UHS)
set(DUNE_Mixing-in-UHS_FOUND TRUE)
set(HAVE_MIXING_IN_UHS TRUE)

# Lines that are set by the CMake build system via the variable DUNE_CUSTOM_PKG_CONFIG_SECTION


# If this file is found in a super build that includes Mixing-in-UHS, the 
# `Mixing-in-UHS-targets.cmake`-file has not yet been generated. This variable
# determines whether the configuration of Mixing-in-UHS has been completed.
get_property(Mixing-in-UHS_IN_CONFIG_MODE GLOBAL PROPERTY Mixing-in-UHS_LIBRARIES DEFINED)

#import the target
if(Mixing-in-UHS_LIBRARIES AND NOT Mixing-in-UHS_IN_CONFIG_MODE)
  get_filename_component(_dir "${CMAKE_CURRENT_LIST_FILE}" PATH)
  include("${_dir}/Mixing-in-UHS-targets.cmake")
endif()

endif()
