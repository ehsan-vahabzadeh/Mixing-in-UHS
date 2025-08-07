add_input_file_links(FILES params.input)

find_package(OpenMP REQUIRED)
# set the test guard for the following tests (only enable test if UMFPack is available)
set(DUMUX_EXAMPLE_LDC_CMAKE_GUARD "( HAVE_UMFPACK )")
dumux_add_test(NAME appl_2pnc_tpfa_H2
              SOURCES main.cc
              COMPILE_DEFINITIONS TYPETAG=BiogeochemicalCCTpfa ENABLECACHING=0 SCHEIDEGGER=0
              CMD_ARGS params.input)


# set(CMAKE_BUILD_TYPE Debug)


dumux_add_test(NAME appl_2pnc_box_H2
              SOURCES main.cc
              COMPILE_DEFINITIONS TYPETAG=mixingbox ENABLECACHING=0 SCHEIDEGGER=1
              CMD_ARGS params.input)           
# set(CMAKE_BUILD_TYPE Debug)
#if(OpenMP_CXX_FOUND)
#    target_link_libraries(appl_2pnc_box_H2 PUBLIC OpenMP::OpenMP_CXX)
#endif()
