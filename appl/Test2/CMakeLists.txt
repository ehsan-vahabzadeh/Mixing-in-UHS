add_input_file_links(FILES params.input)

find_package(OpenMP REQUIRED)

dumux_add_test(NAME appl_2pncgeobio_biogeochemical_tpfa2
              SOURCES main.cc
              COMPILE_DEFINITIONS TYPETAG=mixingtpfa ENABLECACHING=0 SCHEIDEGGER=0
              CMD_ARGS params.input)

#target_link_libraries(appl_2pncgeobio_biogeochemical_tpfa2 /home/ehsan/Dumux_Publications/REAKTORO/reaktoro/build/Reaktoro/libReaktoro.so
#			/home/ehsan/Dumux_Publications/PHREEQC/phreeqcrm-3.7.3-15968/build/libPhreeqcRM.a)
# set(CMAKE_BUILD_TYPE Debug)




dumux_add_test(NAME appl_2pncgeobio_biogeochemical_box2
              SOURCES main.cc
              COMPILE_DEFINITIONS TYPETAG=mixingbox ENABLECACHING=0 SCHEIDEGGER=1
              CMD_ARGS params.input)
#target_link_libraries(appl_2pncgeobio_biogeochemical_box2 /home/ehsan/Dumux_Publications/REAKTORO/reaktoro/build/Reaktoro/libReaktoro.so
#              /home/ehsan/Dumux_Publications/PHREEQC/phreeqcrm-3.7.3-15968/build/libPhreeqcRM.a)              
# set(CMAKE_BUILD_TYPE Debug)
#if(OpenMP_CXX_FOUND)
#    target_link_libraries(appl_2pncgeobio_biogeochemical_tpfa2 PUBLIC OpenMP::OpenMP_CXX)
#endif()
