add_subdirectory(dispersiontensors)
file(GLOB DUMUX_MATERIAL_FLUIDMATRIXINTERACTIONS_HEADERS *.hh *.inc)
install(FILES ${DUMUX_MATERIAL_FLUIDMATRIXINTERACTIONS_HEADERS}
        DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/dumux/material/fluidmatrixinteractions)

