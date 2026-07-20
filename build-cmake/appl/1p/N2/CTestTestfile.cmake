# CMake generated Testfile for 
# Source directory: /home/n71743ev/DUMUX/dumux/Mixing-in-UHS/appl/1p/N2
# Build directory: /home/n71743ev/DUMUX/dumux/Mixing-in-UHS/build-cmake/appl/1p/N2
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test(appl_1pnc_tpfa_N2 "/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/build-cmake/appl/1p/N2/appl_1pnc_tpfa_N2" "params.input")
set_tests_properties(appl_1pnc_tpfa_N2 PROPERTIES  LABELS "" PROCESSORS "1" REQUIRED_FILES "/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/build-cmake/appl/1p/N2/appl_1pnc_tpfa_N2" SKIP_RETURN_CODE "77" TIMEOUT "300" WORKING_DIRECTORY "/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/build-cmake/appl/1p/N2" _BACKTRACE_TRIPLES "/home/n71743ev/DUMUX/dumux/dune-common/cmake/modules/DuneTestMacros.cmake;417;add_test;/home/n71743ev/DUMUX/dumux/dumux/cmake/modules/DumuxTestMacros.cmake;210;dune_add_test;/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/appl/1p/N2/CMakeLists.txt;8;dumux_add_test;/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/appl/1p/N2/CMakeLists.txt;0;")
add_test(appl_1pnc_box_N2 "/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/build-cmake/appl/1p/N2/appl_1pnc_box_N2" "params.input")
set_tests_properties(appl_1pnc_box_N2 PROPERTIES  LABELS "" PROCESSORS "1" REQUIRED_FILES "/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/build-cmake/appl/1p/N2/appl_1pnc_box_N2" SKIP_RETURN_CODE "77" TIMEOUT "300" WORKING_DIRECTORY "/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/build-cmake/appl/1p/N2" _BACKTRACE_TRIPLES "/home/n71743ev/DUMUX/dumux/dune-common/cmake/modules/DuneTestMacros.cmake;417;add_test;/home/n71743ev/DUMUX/dumux/dumux/cmake/modules/DumuxTestMacros.cmake;210;dune_add_test;/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/appl/1p/N2/CMakeLists.txt;17;dumux_add_test;/home/n71743ev/DUMUX/dumux/Mixing-in-UHS/appl/1p/N2/CMakeLists.txt;0;")
subdirs("fluidsystems")
