// -*- mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*-
// vi: set et ts=4 sw=4 sts=4:
/*****************************************************************************
 *   See the file COPYING for full copying permissions.                      *
 *                                                                           *
 *   This program is free software: you can redistribute it and/or modify    *
 *   it under the terms of the GNU General Public License as published by    *
 *   the Free Software Foundation, either version 3 of the License, or       *
 *   (at your option) any later version.                                     *
 *                                                                           *
 *   This program is distributed in the hope that it will be useful,         *
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of          *
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the            *
 *   GNU General Public License for more details.                            *
 *                                                                           *
 *   You should have received a copy of the GNU General Public License       *
 *   along with this program.  If not, see <http://www.gnu.org/licenses/>.   *
 *****************************************************************************/
/*!
 * \file
 * \ingroup TwoPNCTest
 * \brief Test case for mixing simulation during UHS
 */

#ifndef DUMUX_BIOCHEMICAL_PROPERTIES_HH
#define DUMUX_BIOCHEMICAL_PROPERTIES_HH

#include <dune/grid/yaspgrid.hh>
// #include <dune/subgrid/subgrid.hh>

#include <dumux/discretization/ccmpfa.hh>
#include <dumux/discretization/cctpfa.hh>
#include <dumux/discretization/box.hh>

// #include <dumux/material/fluidsystems/mixture.hh>

#include "fluidsystems/mixture.hh"

#include <dumux/porousmediumflow/2pnc/model.hh>

#include <dumux/material/fluidmatrixinteractions/dispersiontensors/fulltensor.hh>
#include <dumux/material/fluidmatrixinteractions/dispersiontensors/scheidegger.hh>
#include <dumux/flux/maxwellstefanslaw.hh>
#include <dumux/discretization/extrusion.hh>
#ifndef ENABLECACHING
#define ENABLECACHING 0
#endif

#include "spatialparams.hh"
#include "problem.hh"

namespace Dumux::Properties {

// Create new type tags
namespace TTag {
struct mixing { using InheritsFrom = std::tuple<TwoPNC>; };
struct mixingbox { using InheritsFrom = std::tuple<mixing, BoxModel>; };
struct mixingtpfa { using InheritsFrom = std::tuple<mixing, CCTpfaModel>; };
} // end namespace TTag

// Set the grid type
// template<class TypeTag>
// // // struct Grid<TypeTag, TTag::mixing> { using type = Dune::YaspGrid<3>; };
// struct Grid<TypeTag, TTag::mixing> { using type = Dune::YaspGrid<2>; };

template<class TypeTag>
struct Grid<TypeTag, TTag::mixing>
{ using type =  Dune::YaspGrid<2, Dune::EquidistantOffsetCoordinates<double, 2>>; };
// { using type = Dune::YaspGrid<2, Dune::TensorProductCoordinates<GetPropType<TypeTag, Properties::Scalar>, 2>>; };

// template<class TypeTag>
// // struct Grid<TypeTag, TTag::ExerciseFluidsystemTwoPTwoC> { using type = Dune::YaspGrid<2>; };
// struct Grid<TypeTag, TTag::Biogeochemical>
// {
//     static constexpr int dim = 2;
//     // using HostGrid = Dune::YaspGrid<2, Dune::EquidistantOffsetCoordinates<double, 2>>;
//     using HostGrid = Dune::YaspGrid<dim, Dune::EquidistantOffsetCoordinates<GetPropType<TypeTag, Properties::Scalar>, dim> >;
//     using type = Dune::SubGrid<HostGrid::dimension, HostGrid>;
//     // using type = Dune::SubGrid<HostGrid::dimension, HostGrid>;
// };

// Set the problem property
template<class TypeTag>
struct Problem<TypeTag, TTag::mixing> { using type = mixingProblem<TypeTag>; };

// Set fluid configuration
template<class TypeTag>
struct FluidSystem<TypeTag, TTag::mixing>
{
        using type = FluidSystems::MixingFluidSystem<GetPropType<TypeTag, Properties::Scalar>,
                                        FluidSystems::MixingFluidSystemDefaultPolicy</*fastButSimplifiedRelations=*/true>>;
};

// Set the spatial parameters
template<class TypeTag>
struct SpatialParams<TypeTag, TTag::mixing>
{
    using GridGeometry = GetPropType<TypeTag, Properties::GridGeometry>;
    using Scalar = GetPropType<TypeTag, Properties::Scalar>;
    using type = mixingSpatialParams<GridGeometry, Scalar>;
};

// rotation-symmetric grid geometry forming a cylinder channel
template<class TypeTag>
struct GridGeometry<TypeTag, TTag::mixing>
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

// Define whether mole(true) or mass (false) fractions are used
template<class TypeTag>
struct UseMoles<TypeTag, TTag::mixing> { static constexpr bool value = true; };

template<class TypeTag>
struct EnableCompositionalDispersion<TypeTag, TTag::mixing> { static constexpr bool value = true; };

template<class TypeTag>
struct CompositionalDispersionModel<TypeTag, TTag::mixing>
{
    #if SCHEIDEGGER
    using type = ScheideggersDispersionTensor<TypeTag>;
#else
    using type = FullDispersionTensor<TypeTag>;
#endif

};

// Comment out for molecular Diffusion Model from HyUSPRe
template<class TypeTag>
struct EffectiveDiffusivityModel<TypeTag, TTag::mixing> { using type = DiffusivityMillingtonQuirk<GetPropType<TypeTag, Properties::Scalar>>; };
//! Here we set FicksLaw or MaxwellStefansLaw
template<class TypeTag>
struct MolecularDiffusionType<TypeTag, TTag::mixing> { using type = FicksLaw<TypeTag>; };
// Enable caching or not (reference solutions created without caching)
template<class TypeTag>
struct EnableGridGeometryCache<TypeTag, TTag::mixing> { static constexpr bool value = ENABLECACHING; };
template<class TypeTag>
struct EnableGridVolumeVariablesCache<TypeTag, TTag::mixing> { static constexpr bool value = ENABLECACHING; };
template<class TypeTag>
struct EnableGridFluxVariablesCache<TypeTag, TTag::mixing> { static constexpr bool value = ENABLECACHING; };

} // end namespace Dumux::Properties

#endif
