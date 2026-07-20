


#ifndef DUNE_COMMON_CONFIG_HH
#define DUNE_COMMON_CONFIG_HH

/* Define to 1 if you have module dune-common available */
#ifndef HAVE_DUNE_COMMON
#define HAVE_DUNE_COMMON 1
#endif



/* Define to the version of dune-common */
#define DUNE_COMMON_VERSION "2.10"

/* Define to the major version of dune-common */
#define DUNE_COMMON_VERSION_MAJOR 2

/* Define to the minor version of dune-common */
#define DUNE_COMMON_VERSION_MINOR 10

/* Define to the revision of dune-common */
#define DUNE_COMMON_VERSION_REVISION 0

/* Standard debug streams with a level below will collapse to doing nothing */
#define DUNE_MINIMAL_DEBUG_LEVEL 4

/* does the standard library provide experimental::is_detected ? */
#define DUNE_HAVE_CXX_EXPERIMENTAL_IS_DETECTED 1

/* does the language support lambdas in unevaluated contexts ? */
/* #undef DUNE_HAVE_CXX_UNEVALUATED_CONTEXT_LAMBDA */

/* does the standard library provide identity ? */
/* #undef DUNE_HAVE_CXX_STD_IDENTITY */

/* Define if you have a BLAS library. */
#define HAVE_BLAS 1

/* Define if you have LAPACK library. */
#define HAVE_LAPACK 1

/* Define to 1 if you have the Threading Building Blocks (TBB) library */
/* #undef HAVE_TBB */




/* old feature support macros which were tested until 2.10, kept around for one more release */
/* none for 2.10 */

/* Define to ENABLE_UMFPACK if the UMFPack library is available. */
/// \deprecated Use HAVE_SUITESPARSE_UMFPACK instead
#define HAVE_UMFPACK HAVE_SUITESPARSE_UMFPACK

/* Used to call lapack functions */
#define LAPACK_NEEDS_UNDERLINE

/* If enabled certain Python modules will be precompiled */
/* #undef DUNE_ENABLE_PYTHONMODULE_PRECOMPILE */






#endif // DUNE_COMMON_CONFIG_HH



#ifndef DUNE_GEOMETRY_CONFIG_HH
#define DUNE_GEOMETRY_CONFIG_HH

/* Define to 1 if you have module dune-geometry available */
#ifndef HAVE_DUNE_GEOMETRY
#define HAVE_DUNE_GEOMETRY 1
#endif




/* Define to the version of dune-geometry */
#define DUNE_GEOMETRY_VERSION "2.10"

/* Define to the major version of dune-geometry */
#define DUNE_GEOMETRY_VERSION_MAJOR 2

/* Define to the minor version of dune-geometry */
#define DUNE_GEOMETRY_VERSION_MINOR 10

/* Define to the revision of dune-geometry */
#define DUNE_GEOMETRY_VERSION_REVISION 0





#if __has_include(<dune-common-config.hh>)
  #include <dune-common-config.hh>
#endif


#endif // DUNE_GEOMETRY_CONFIG_HH



#ifndef DUNE_UGGRID_CONFIG_HH
#define DUNE_UGGRID_CONFIG_HH

/* Define to 1 if you have module dune-uggrid available */
#ifndef HAVE_DUNE_UGGRID
#define HAVE_DUNE_UGGRID 1
#endif


/* Define to the version of dune-common */
#define DUNE_UGGRID_VERSION "2.10"

/* Define to the major version of dune-common */
#define DUNE_UGGRID_VERSION_MAJOR 2

/* Define to the minor version of dune-common */
#define DUNE_UGGRID_VERSION_MINOR 10

/* Define to the revision of dune-common */
#define DUNE_UGGRID_VERSION_REVISION 0

/* begin private section */

/* see parallel/ddd/dddi.h */
/* #undef DDD_MAX_PROCBITS_IN_GID */

/* Define to 1 if you can safely include both <sys/time.h> and <time.h>. */
/* #undef TIME_WITH_SYS_TIME */

/* Define to 1 if UGGrid should use the complete set of green refinement rules for tetrahedra */
/* #undef DUNE_UGGRID_TET_RULESET */

/* end private section */





#if __has_include(<dune-common-config.hh>)
  #include <dune-common-config.hh>
#endif


#endif // DUNE_UGGRID_CONFIG_HH



#ifndef DUNE_GRID_CONFIG_HH
#define DUNE_GRID_CONFIG_HH

/* Define to 1 if you have module dune-grid available */
#ifndef HAVE_DUNE_GRID
#define HAVE_DUNE_GRID 1
#endif




/* Define to the version of dune-grid */
#define DUNE_GRID_VERSION "2.10"

/* Define to the major version of dune-grid */
#define DUNE_GRID_VERSION_MAJOR 2

/* Define to the minor version of dune-grid */
#define DUNE_GRID_VERSION_MINOR 10

/* Define to the revision of dune-grid */
#define DUNE_GRID_VERSION_REVISION 0

/* Alberta version found by configure, either 0x200 for 2.0 or 0x300 for 3.0 */
/* #undef DUNE_ALBERTA_VERSION */

/* Define to 1 if you have mkstemp function */
#define HAVE_MKSTEMP 1







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
#define HAVE_DUNE_LOCALFUNCTIONS 1
#endif




/* Define to the version of dune-localfunctions */
#define DUNE_LOCALFUNCTIONS_VERSION "2.10"

/* Define to the major version of dune-localfunctions */
#define DUNE_LOCALFUNCTIONS_VERSION_MAJOR 2

/* Define to the minor version of dune-localfunctions */
#define DUNE_LOCALFUNCTIONS_VERSION_MINOR 10

/* Define to the revision of dune-localfunctions */
#define DUNE_LOCALFUNCTIONS_VERSION_REVISION 0





#if __has_include(<dune-geometry-config.hh>)
  #include <dune-geometry-config.hh>
#endif


#endif // DUNE_LOCALFUNCTIONS_CONFIG_HH



#ifndef DUNE_ISTL_CONFIG_HH
#define DUNE_ISTL_CONFIG_HH

/* Define to 1 if you have module dune-istl available */
#ifndef HAVE_DUNE_ISTL
#define HAVE_DUNE_ISTL 1
#endif





/* Define to the integer type that SuperLU was compiled for
   See e.g. what int_t is defined to in slu_sdefs.h */
#define SUPERLU_INT_TYPE int

/* Define to the version of dune-istl */
#define DUNE_ISTL_VERSION "2.10"

/* Define to the major version of dune-istl */
#define DUNE_ISTL_VERSION_MAJOR 2

/* Define to the minor version of dune-istl */
#define DUNE_ISTL_VERSION_MINOR 10

/* Define to the revision of dune-istl */
#define DUNE_ISTL_VERSION_REVISION 0

/* Enable/Disable the backwards compatibility of the category enum/method in dune-istl solvers, preconditioner, etc. */
#define DUNE_ISTL_SUPPORT_OLD_CATEGORY_INTERFACE 1





#if __has_include(<dune-common-config.hh>)
  #include <dune-common-config.hh>
#endif


#endif // DUNE_ISTL_CONFIG_HH



#ifndef DUMUX_CONFIG_HH
#define DUMUX_CONFIG_HH

/* Define to 1 if you have module dumux available */
#ifndef HAVE_DUMUX
#define HAVE_DUMUX 1
#endif





/* Define to the version of dumux */
#define DUMUX_VERSION "3.10"

/* Define to the major version of dumux */
#define DUMUX_VERSION_MAJOR 3

/* Define to the minor version of dumux */
#define DUMUX_VERSION_MINOR 10

/* Define to the revision of dumux */
#define DUMUX_VERSION_REVISION 0

/* Define the path to dumux */
#define DUMUX_SOURCE_DIR "/home/n71743ev/DUMUX/dumux/Mixing-in-UHS"

/* Define the major version of opm-grid */
#define OPM_GRID_VERSION_MAJOR 

/* Define the minor version of opm-grid */
#define OPM_GRID_VERSION_MINOR 

/* Define to 1 if gnuplot was found */
/* #undef DUMUX_HAVE_GNUPLOT */

/* Define path to gnuplot executable */
/* #undef GNUPLOT_EXECUTABLE */

/* Define to 1 if gstat was found */
/* #undef DUMUX_HAVE_GSTAT */

/* Define path to gstat executable */
/* #undef GSTAT_EXECUTABLE */

/* Define to 1 if quadmath was found */
/* #undef DUMUX_HAVE_QUAD */

/* Set the DUMUX_MULTITHREADING_BACKEND */
#ifndef DUMUX_MULTITHREADING_BACKEND
#define DUMUX_MULTITHREADING_BACKEND OpenMP
#endif

/* Set DUMUX_HAVE_CPP_PARALLEL_ALGORITHMS if available */
/* #undef DUMUX_HAVE_CPP_PARALLEL_ALGORITHMS */





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
#define HAVE_MIXING_IN_UHS 1
#endif

/* begin dumux-hyuspre
   put the definitions for config.h specific to
   your project here. Everything above will be
   overwritten
*/



/* Define to the version of dumux-hyuspre */
#define DUMUX_HYUSPRE_VERSION ""

/* Define to the major version of dumux-hyuspre */
#define DUMUX_HYUSPRE_VERSION_MAJOR 

/* Define to the minor version of dumux-hyuspre */
#define DUMUX_HYUSPRE_VERSION_MINOR 

/* Define to the revision of dumux-hyuspre */
#define DUMUX_HYUSPRE_VERSION_REVISION 

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
#define PACKAGE "Mixing-in-UHS"

/* Define to the address where bug reports for this package should be sent. */
#define PACKAGE_BUGREPORT " "

/* Define to the full name of this package. */
#define PACKAGE_NAME "Mixing-in-UHS"

/* Define to the full name and version of this package. */
#define PACKAGE_STRING "Mixing-in-UHS 0.1"

/* Define to the one symbol short name of this package. */
#define PACKAGE_TARNAME "Mixing-in-UHS"

/* Define to the home page for this package. */
#define PACKAGE_URL ""

/* Define to the version of this package. */
#define PACKAGE_VERSION "0.1"



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

/* ONEDGRID not available, enable with cmake variable DUNE_GRID_GRIDTYPE_SELECTOR=ON */
/* YASPGRID not available, enable with cmake variable DUNE_GRID_GRIDTYPE_SELECTOR=ON */



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

