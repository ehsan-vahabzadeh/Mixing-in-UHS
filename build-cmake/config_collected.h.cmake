


#ifndef DUNE_COMMON_CONFIG_HH
#define DUNE_COMMON_CONFIG_HH

/* Define to 1 if you have module dune-common available */
#ifndef HAVE_DUNE_COMMON
#cmakedefine01 HAVE_DUNE_COMMON
#endif



/* Define to the version of dune-common */
#define DUNE_COMMON_VERSION "${DUNE_COMMON_VERSION}"

/* Define to the major version of dune-common */
#define DUNE_COMMON_VERSION_MAJOR ${DUNE_COMMON_VERSION_MAJOR}

/* Define to the minor version of dune-common */
#define DUNE_COMMON_VERSION_MINOR ${DUNE_COMMON_VERSION_MINOR}

/* Define to the revision of dune-common */
#define DUNE_COMMON_VERSION_REVISION ${DUNE_COMMON_VERSION_REVISION}

/* Standard debug streams with a level below will collapse to doing nothing */
#define DUNE_MINIMAL_DEBUG_LEVEL ${DUNE_MINIMAL_DEBUG_LEVEL}

/* does the standard library provide experimental::is_detected ? */
#cmakedefine DUNE_HAVE_CXX_EXPERIMENTAL_IS_DETECTED 1

/* does the language support lambdas in unevaluated contexts ? */
#cmakedefine DUNE_HAVE_CXX_UNEVALUATED_CONTEXT_LAMBDA 1

/* does the standard library provide identity ? */
#cmakedefine DUNE_HAVE_CXX_STD_IDENTITY 1

/* Define if you have a BLAS library. */
#cmakedefine HAVE_BLAS 1

/* Define if you have LAPACK library. */
#cmakedefine HAVE_LAPACK 1

/* Define to 1 if you have the Threading Building Blocks (TBB) library */
#cmakedefine HAVE_TBB 1




/* old feature support macros which were tested until 2.10, kept around for one more release */
/* none for 2.10 */

/* Define to ENABLE_UMFPACK if the UMFPack library is available. */
/// \deprecated Use HAVE_SUITESPARSE_UMFPACK instead
#define HAVE_UMFPACK HAVE_SUITESPARSE_UMFPACK

/* Used to call lapack functions */
#cmakedefine LAPACK_NEEDS_UNDERLINE

/* If enabled certain Python modules will be precompiled */
#cmakedefine DUNE_ENABLE_PYTHONMODULE_PRECOMPILE






#endif // DUNE_COMMON_CONFIG_HH



#ifndef DUNE_GEOMETRY_CONFIG_HH
#define DUNE_GEOMETRY_CONFIG_HH

/* Define to 1 if you have module dune-geometry available */
#ifndef HAVE_DUNE_GEOMETRY
#cmakedefine01 HAVE_DUNE_GEOMETRY
#endif




/* Define to the version of dune-geometry */
#define DUNE_GEOMETRY_VERSION "${DUNE_GEOMETRY_VERSION}"

/* Define to the major version of dune-geometry */
#define DUNE_GEOMETRY_VERSION_MAJOR ${DUNE_GEOMETRY_VERSION_MAJOR}

/* Define to the minor version of dune-geometry */
#define DUNE_GEOMETRY_VERSION_MINOR ${DUNE_GEOMETRY_VERSION_MINOR}

/* Define to the revision of dune-geometry */
#define DUNE_GEOMETRY_VERSION_REVISION ${DUNE_GEOMETRY_VERSION_REVISION}





#if __has_include(<dune-common-config.hh>)
  #include <dune-common-config.hh>
#endif


#endif // DUNE_GEOMETRY_CONFIG_HH



#ifndef DUNE_UGGRID_CONFIG_HH
#define DUNE_UGGRID_CONFIG_HH

/* Define to 1 if you have module dune-uggrid available */
#ifndef HAVE_DUNE_UGGRID
#cmakedefine01 HAVE_DUNE_UGGRID
#endif


/* Define to the version of dune-common */
#define DUNE_UGGRID_VERSION "${DUNE_UGGRID_VERSION}"

/* Define to the major version of dune-common */
#define DUNE_UGGRID_VERSION_MAJOR ${DUNE_UGGRID_VERSION_MAJOR}

/* Define to the minor version of dune-common */
#define DUNE_UGGRID_VERSION_MINOR ${DUNE_UGGRID_VERSION_MINOR}

/* Define to the revision of dune-common */
#define DUNE_UGGRID_VERSION_REVISION ${DUNE_UGGRID_VERSION_REVISION}

/* begin private section */

/* see parallel/ddd/dddi.h */
#cmakedefine DDD_MAX_PROCBITS_IN_GID ${UG_DDD_MAX_MACROBITS}

/* Define to 1 if you can safely include both <sys/time.h> and <time.h>. */
#cmakedefine TIME_WITH_SYS_TIME 1

/* Define to 1 if UGGrid should use the complete set of green refinement rules for tetrahedra */
#cmakedefine DUNE_UGGRID_TET_RULESET 1

/* end private section */





#if __has_include(<dune-common-config.hh>)
  #include <dune-common-config.hh>
#endif


#endif // DUNE_UGGRID_CONFIG_HH



#ifndef DUNE_GRID_CONFIG_HH
#define DUNE_GRID_CONFIG_HH

/* Define to 1 if you have module dune-grid available */
#ifndef HAVE_DUNE_GRID
#cmakedefine01 HAVE_DUNE_GRID
#endif




/* Define to the version of dune-grid */
#define DUNE_GRID_VERSION "${DUNE_GRID_VERSION}"

/* Define to the major version of dune-grid */
#define DUNE_GRID_VERSION_MAJOR ${DUNE_GRID_VERSION_MAJOR}

/* Define to the minor version of dune-grid */
#define DUNE_GRID_VERSION_MINOR ${DUNE_GRID_VERSION_MINOR}

/* Define to the revision of dune-grid */
#define DUNE_GRID_VERSION_REVISION ${DUNE_GRID_VERSION_REVISION}

/* Alberta version found by configure, either 0x200 for 2.0 or 0x300 for 3.0 */
#cmakedefine DUNE_ALBERTA_VERSION @DUNE_ALBERTA_VERSION@

/* Define to 1 if you have mkstemp function */
#cmakedefine01 HAVE_MKSTEMP







#if __has_include(<dune-geometry-config.hh>)
  #include <dune-geometry-config.hh>
#endif

#if __has_include(<dune-uggrid-config.hh>)
  #include <dune-uggrid-config.hh>
#endif


#endif // DUNE_GRID_CONFIG_HH



#ifndef DUNE_LOCALFUNCTIONS_CONFIG_HH
#define DUNE_LOCALFUNCTIONS_CONFIG_HH

/* Define to 1 if you have module dune-localfunctions available */
#ifndef HAVE_DUNE_LOCALFUNCTIONS
#cmakedefine01 HAVE_DUNE_LOCALFUNCTIONS
#endif




/* Define to the version of dune-localfunctions */
#define DUNE_LOCALFUNCTIONS_VERSION "${DUNE_LOCALFUNCTIONS_VERSION}"

/* Define to the major version of dune-localfunctions */
#define DUNE_LOCALFUNCTIONS_VERSION_MAJOR ${DUNE_LOCALFUNCTIONS_VERSION_MAJOR}

/* Define to the minor version of dune-localfunctions */
#define DUNE_LOCALFUNCTIONS_VERSION_MINOR ${DUNE_LOCALFUNCTIONS_VERSION_MINOR}

/* Define to the revision of dune-localfunctions */
#define DUNE_LOCALFUNCTIONS_VERSION_REVISION ${DUNE_LOCALFUNCTIONS_VERSION_REVISION}





#if __has_include(<dune-geometry-config.hh>)
  #include <dune-geometry-config.hh>
#endif


#endif // DUNE_LOCALFUNCTIONS_CONFIG_HH



#ifndef DUNE_ISTL_CONFIG_HH
#define DUNE_ISTL_CONFIG_HH

/* Define to 1 if you have module dune-istl available */
#ifndef HAVE_DUNE_ISTL
#cmakedefine01 HAVE_DUNE_ISTL
#endif





/* Define to the integer type that SuperLU was compiled for
   See e.g. what int_t is defined to in slu_sdefs.h */
#cmakedefine SUPERLU_INT_TYPE @SUPERLU_INT_TYPE@

/* Define to the version of dune-istl */
#define DUNE_ISTL_VERSION "${DUNE_ISTL_VERSION}"

/* Define to the major version of dune-istl */
#define DUNE_ISTL_VERSION_MAJOR ${DUNE_ISTL_VERSION_MAJOR}

/* Define to the minor version of dune-istl */
#define DUNE_ISTL_VERSION_MINOR ${DUNE_ISTL_VERSION_MINOR}

/* Define to the revision of dune-istl */
#define DUNE_ISTL_VERSION_REVISION ${DUNE_ISTL_VERSION_REVISION}

/* Enable/Disable the backwards compatibility of the category enum/method in dune-istl solvers, preconditioner, etc. */
#cmakedefine DUNE_ISTL_SUPPORT_OLD_CATEGORY_INTERFACE @DUNE_ISTL_SUPPORT_OLD_CATEGORY_INTERFACE@





#if __has_include(<dune-common-config.hh>)
  #include <dune-common-config.hh>
#endif


#endif // DUNE_ISTL_CONFIG_HH



#ifndef DUMUX_CONFIG_HH
#define DUMUX_CONFIG_HH

/* Define to 1 if you have module dumux available */
#ifndef HAVE_DUMUX
#cmakedefine01 HAVE_DUMUX
#endif





/* Define to the version of dumux */
#define DUMUX_VERSION "${DUMUX_VERSION}"

/* Define to the major version of dumux */
#define DUMUX_VERSION_MAJOR ${DUMUX_VERSION_MAJOR}

/* Define to the minor version of dumux */
#define DUMUX_VERSION_MINOR ${DUMUX_VERSION_MINOR}

/* Define to the revision of dumux */
#define DUMUX_VERSION_REVISION ${DUMUX_VERSION_REVISION}

/* Define the path to dumux */
#define DUMUX_SOURCE_DIR "${CMAKE_SOURCE_DIR}"

/* Define the major version of opm-grid */
#define OPM_GRID_VERSION_MAJOR ${OPM_GRID_VERSION_MAJOR}

/* Define the minor version of opm-grid */
#define OPM_GRID_VERSION_MINOR ${OPM_GRID_VERSION_MINOR}

/* Define to 1 if gnuplot was found */
#cmakedefine DUMUX_HAVE_GNUPLOT 1

/* Define path to gnuplot executable */
#cmakedefine GNUPLOT_EXECUTABLE "@GNUPLOT_EXECUTABLE@"

/* Define to 1 if gstat was found */
#cmakedefine DUMUX_HAVE_GSTAT 1

/* Define path to gstat executable */
#cmakedefine GSTAT_EXECUTABLE "@GSTAT_EXECUTABLE@"

/* Define to 1 if quadmath was found */
#cmakedefine DUMUX_HAVE_QUAD 1

/* Set the DUMUX_MULTITHREADING_BACKEND */
#ifndef DUMUX_MULTITHREADING_BACKEND
#define DUMUX_MULTITHREADING_BACKEND ${DUMUX_MULTITHREADING_BACKEND}
#endif

/* Set DUMUX_HAVE_CPP_PARALLEL_ALGORITHMS if available */
#cmakedefine DUMUX_HAVE_CPP_PARALLEL_ALGORITHMS 1





#if __has_include(<dune-common-config.hh>)
  #include <dune-common-config.hh>
#endif

#if __has_include(<dune-geometry-config.hh>)
  #include <dune-geometry-config.hh>
#endif

#if __has_include(<dune-grid-config.hh>)
  #include <dune-grid-config.hh>
#endif

#if __has_include(<dune-localfunctions-config.hh>)
  #include <dune-localfunctions-config.hh>
#endif

#if __has_include(<dune-istl-config.hh>)
  #include <dune-istl-config.hh>
#endif

#if __has_include(<dune-alugrid-config.hh>)
  #include <dune-alugrid-config.hh>
#endif

#if __has_include(<dune-foamgrid-config.hh>)
  #include <dune-foamgrid-config.hh>
#endif

#if __has_include(<dune-uggrid-config.hh>)
  #include <dune-uggrid-config.hh>
#endif

#if __has_include(<dune-functions-config.hh>)
  #include <dune-functions-config.hh>
#endif

#if __has_include(<opm-common-config.hh>)
  #include <opm-common-config.hh>
#endif

#if __has_include(<opm-grid-config.hh>)
  #include <opm-grid-config.hh>
#endif

#if __has_include(<dune-subgrid-config.hh>)
  #include <dune-subgrid-config.hh>
#endif

#if __has_include(<dune-spgrid-config.hh>)
  #include <dune-spgrid-config.hh>
#endif

#if __has_include(<dune-mmesh-config.hh>)
  #include <dune-mmesh-config.hh>
#endif


#endif // DUMUX_CONFIG_HH



#ifndef MIXING_IN_UHS_CONFIG_HH
#define MIXING_IN_UHS_CONFIG_HH

/* Define to 1 if you have module Mixing-in-UHS available */
#ifndef HAVE_MIXING_IN_UHS
#cmakedefine01 HAVE_MIXING_IN_UHS
#endif

/* begin dumux-hyuspre
   put the definitions for config.h specific to
   your project here. Everything above will be
   overwritten
*/



/* Define to the version of dumux-hyuspre */
#define DUMUX_HYUSPRE_VERSION "@DUMUX_HYUSPRE_VERSION@"

/* Define to the major version of dumux-hyuspre */
#define DUMUX_HYUSPRE_VERSION_MAJOR @DUMUX_HYUSPRE_VERSION_MAJOR@

/* Define to the minor version of dumux-hyuspre */
#define DUMUX_HYUSPRE_VERSION_MINOR @DUMUX_HYUSPRE_VERSION_MINOR@

/* Define to the revision of dumux-hyuspre */
#define DUMUX_HYUSPRE_VERSION_REVISION @DUMUX_HYUSPRE_VERSION_REVISION@

/* end dumux-hyuspre
   Everything below here will be overwritten
*/



#if __has_include(<dumux-config.hh>)
  #include <dumux-config.hh>
#endif


#endif // MIXING_IN_UHS_CONFIG_HH


#ifndef MIXING_IN_UHS_CONFIG_PRIVATE_HH
#define MIXING_IN_UHS_CONFIG_PRIVATE_HH


/* Name of package */
#define PACKAGE "@DUNE_MOD_NAME@"

/* Define to the address where bug reports for this package should be sent. */
#define PACKAGE_BUGREPORT "@DUNE_MAINTAINER@"

/* Define to the full name of this package. */
#define PACKAGE_NAME "@DUNE_MOD_NAME@"

/* Define to the full name and version of this package. */
#define PACKAGE_STRING "@DUNE_MOD_NAME@ @DUNE_MOD_VERSION@"

/* Define to the one symbol short name of this package. */
#define PACKAGE_TARNAME "@DUNE_MOD_NAME@"

/* Define to the home page for this package. */
#define PACKAGE_URL "@DUNE_MOD_URL@"

/* Define to the version of this package. */
#define PACKAGE_VERSION "@DUNE_MOD_VERSION@"



#include <Mixing-in-UHS-config.hh>

#endif // MIXING_IN_UHS_CONFIG_PRIVATE_HH



#ifndef DUNE_COMMON_CONFIG_BOTTOM_HH
#define DUNE_COMMON_CONFIG_BOTTOM_HH



#endif // DUNE_COMMON_CONFIG_BOTTOM_HH



#ifndef DUNE_GEOMETRY_CONFIG_BOTTOM_HH
#define DUNE_GEOMETRY_CONFIG_BOTTOM_HH



#endif // DUNE_GEOMETRY_CONFIG_BOTTOM_HH



#ifndef DUNE_UGGRID_CONFIG_BOTTOM_HH
#define DUNE_UGGRID_CONFIG_BOTTOM_HH



#endif // DUNE_UGGRID_CONFIG_BOTTOM_HH



#ifndef DUNE_GRID_CONFIG_BOTTOM_HH
#define DUNE_GRID_CONFIG_BOTTOM_HH



/* Grid type magic for DGF parser */
@GRID_CONFIG_H_BOTTOM@



#endif // DUNE_GRID_CONFIG_BOTTOM_HH



#ifndef DUNE_LOCALFUNCTIONS_CONFIG_BOTTOM_HH
#define DUNE_LOCALFUNCTIONS_CONFIG_BOTTOM_HH



#endif // DUNE_LOCALFUNCTIONS_CONFIG_BOTTOM_HH



#ifndef DUNE_ISTL_CONFIG_BOTTOM_HH
#define DUNE_ISTL_CONFIG_BOTTOM_HH



#endif // DUNE_ISTL_CONFIG_BOTTOM_HH



#ifndef DUMUX_CONFIG_BOTTOM_HH
#define DUMUX_CONFIG_BOTTOM_HH



#endif // DUMUX_CONFIG_BOTTOM_HH



#ifndef MIXING_IN_UHS_CONFIG_BOTTOM_HH
#define MIXING_IN_UHS_CONFIG_BOTTOM_HH



#endif // MIXING_IN_UHS_CONFIG_BOTTOM_HH

