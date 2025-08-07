// -*- mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*-
// vi: set et ts=4 sw=4 sts=4:
//
// SPDX-FileCopyrightInfo: Copyright © DuMux Project contributors, see AUTHORS.md in root folder
// SPDX-License-Identifier: GPL-3.0-or-later
//
/**
 * \file
 * \ingroup OnePNCTests
 * \brief Definition of a problem for the 1pnc problem:
 * Component transport of nitrogen dissolved in the water phase.
 */

#ifndef DUMUX_1P2C_TEST_PROBLEM_PROPERTIES_HH
#define DUMUX_1P2C_TEST_PROBLEM_PROPERTIES_HH

#if HAVE_DUNE_UGGRID
#include <dune/grid/uggrid.hh>
#endif
#include <dune/grid/yaspgrid.hh>

#include <dumux/common/math.hh>

#include <dumux/discretization/cctpfa.hh>
#include <dumux/discretization/ccmpfa.hh>
#include <dumux/discretization/box.hh>
#include <dumux/discretization/evalsolution.hh>
#include <dumux/discretization/evalgradients.hh>
#include <dumux/porousmediumflow/1pnc/model.hh>


#include <dumux/material/fluidsystems/h2on2.hh>
#include <dumux/material/fluidsystems/1padapter.hh>
#include "fluidsystems/mixture.hh"
#include "problem.hh"
#include "spatialparams.hh"

namespace Dumux::Properties {

// Create new type tags
namespace TTag {
struct OnePTwoCTest { using InheritsFrom = std::tuple<OnePNC>; };
struct OnePTwoCTestBox { using InheritsFrom = std::tuple<OnePTwoCTest, BoxModel>; };
struct OnePTwoCTestCCTpfa { using InheritsFrom = std::tuple<OnePTwoCTest, CCTpfaModel>; };
struct OnePTwoCTestCCMpfa { using InheritsFrom = std::tuple<OnePTwoCTest, CCMpfaModel>; };
} // end namespace TTag
// template<class TypeTag>
// struct Grid<TypeTag, TTag::OnePTwoCTest> { using type = Dune::YaspGrid<2>; };

template<class TypeTag>
struct Grid<TypeTag, TTag::OnePTwoCTest>
{ using type =  Dune::YaspGrid<2, Dune::EquidistantOffsetCoordinates<double, 2>>; };

// Set the problem property
template<class TypeTag>
struct Problem<TypeTag, TTag::OnePTwoCTest> { using type = OnePTwoCTestProblem<TypeTag>; };

// Set fluid configuration
// template<class TypeTag>
// struct FluidSystem<TypeTag, TTag::OnePTwoCTest>
// {
//     using Scalar = GetPropType<TypeTag, Properties::Scalar>;
//     using H2ON2 = FluidSystems::H2ON2<Scalar, FluidSystems::H2ON2DefaultPolicy</*simplified=*/true>>;
//     using type = FluidSystems::OnePAdapter<H2ON2, H2ON2::liquidPhaseIdx>;
// };
template<class TypeTag>
struct FluidSystem<TypeTag, TTag::OnePTwoCTest>
{
        using MixingFluidSystem = FluidSystems::MixingFluidSystem<GetPropType<TypeTag, Properties::Scalar>,
                                        FluidSystems::MixingFluidSystemDefaultPolicy</*fastButSimplifiedRelations=*/false>>;
        using type = FluidSystems::OnePAdapter<MixingFluidSystem, MixingFluidSystem::gasPhaseIdx>;
};
// rotation-symmetric grid geometry forming a cylinder channel
template<class TypeTag>
struct GridGeometry<TypeTag, TTag::OnePTwoCTest>
{
private:
    static constexpr bool enableCache = getPropValue<TypeTag, Properties::EnableGridGeometryCache>();
    using Scalar = GetPropType<TypeTag, Properties::Scalar>;
    using GridView = typename GetPropType<TypeTag, Properties::Grid>::LeafGridView;

    // We take the default traits as basis and exchange the extrusion type
    // The first axis (x-axis) is the radial axis, hence the zero. That means we rotate about the second axis (y-axis).
    // struct GGTraits : public CCTpfaDefaultGridGeometryTraits<GridView>
    struct GGTraits : public BoxDefaultGridGeometryTraits<GridView>
    { using Extrusion = RotationalExtrusion<0>; };
public:
    // Pass the above traits to the box grid geometry such that it uses the
    // rotation-symmetric sub-control volumes and faces.
    // using type = CCTpfaFVGridGeometry<GridView, enableCache, GGTraits>;
    using type = BoxFVGridGeometry<Scalar, GridView, enableCache, GGTraits>;
};   
// Set the spatial parameters
template<class TypeTag>
struct SpatialParams<TypeTag, TTag::OnePTwoCTest>
{
    using GridGeometry = GetPropType<TypeTag, Properties::GridGeometry>;
    using Scalar = GetPropType<TypeTag, Properties::Scalar>;
    using type = OnePNCTestSpatialParams<GridGeometry, Scalar>;
};

template<class TypeTag>
struct EnableCompositionalDispersion<TypeTag, TTag::OnePTwoCTest> { static constexpr bool value = true; };

template<class TypeTag>
struct CompositionalDispersionModel<TypeTag, TTag::OnePTwoCTest>
{
using type = ScheideggersDispersionTensor<TypeTag>;
};
template<class TypeTag>
struct MolecularDiffusionType<TypeTag, TTag::OnePTwoCTest> { using type = FicksLaw<TypeTag>; };
// Enable caching or not (reference solutions created without caching)
template<class TypeTag>
struct EnableGridGeometryCache<TypeTag, TTag::OnePTwoCTest> { static constexpr bool value = ENABLECACHING; };
template<class TypeTag>
struct EnableGridVolumeVariablesCache<TypeTag, TTag::OnePTwoCTest> { static constexpr bool value = ENABLECACHING; };
template<class TypeTag>
struct EnableGridFluxVariablesCache<TypeTag, TTag::OnePTwoCTest> { static constexpr bool value = ENABLECACHING; };
// Define whether mole(true) or mass (false) fractions are used
template<class TypeTag>
struct UseMoles<TypeTag, TTag::OnePTwoCTest> { static constexpr bool value = true; };
} // end namespace Dumux::Properties

#endif
