add_subdirectory(fluidsystems)
add_input_file_links(FILES params.input)
dune_symlink_to_source_files(FILES runscript.py)
dune_symlink_to_source_files(FILES vtk-merge-multi.py)
find_package(OpenMP REQUIRED)

dumux_add_test(NAME appl_1pnc_tpfa_Test2
              SOURCES main.cc
              COMPILE_DEFINITIONS TYPETAG=OnePTwoCTestCCTpfa ENABLECACHING=1 SCHEIDEGGER=0
              CMD_ARGS params.input)
# set(CMAKE_BUILD_TYPE Debug)




dumux_add_test(NAME appl_1pnc_box_Test2
              SOURCES main.cc
              COMPILE_DEFINITIONS TYPETAG=OnePTwoCTestBox ENABLECACHING=1 SCHEIDEGGER=0
              CMD_ARGS params.input)           
# set(CMAKE_BUILD_TYPE Debug)
if(OpenMP_CXX_FOUND)
    target_link_libraries(appl_1pnc_tpfa_Test2 PUBLIC OpenMP::OpenMP_CXX)
endif()
