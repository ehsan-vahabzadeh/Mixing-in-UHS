add_subdirectory(box)

install(FILES
	fickslaw_fwd.hh
        maxwellstefanslaw_fwd.hh
        DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/dumux/flux)


