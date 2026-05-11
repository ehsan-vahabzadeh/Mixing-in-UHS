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
 * \ingroup Fluidmatrixinteractions
 * \brief Scheidegger-type hydrodynamic dispersion model.
 */
#ifndef DUMUX_MATERIAL_FLUIDMATRIX_DISPERSIONTENSORS_SCHEIDEGGER_HH
#define DUMUX_MATERIAL_FLUIDMATRIX_DISPERSIONTENSORS_SCHEIDEGGER_HH

#include <algorithm>
#include <array>
#include <cmath>
#include <dune/common/math.hh>
#include <dune/common/std/type_traits.hh>
#include <dune/common/fmatrix.hh>
#include <dumux/common/properties.hh>
#include <dumux/common/parameters.hh>
#include <dumux/discretization/method.hh>
#include <dumux/flux/facetensoraverage.hh>
#include <dumux/flux/traits.hh>

namespace Dumux {

namespace Detail {
template <class Problem, class SubControlVolumeFace>
using HasVelocityInSpatialParams = decltype(std::declval<Problem>().spatialParams().velocity(std::declval<SubControlVolumeFace>()));

template<class Problem, class SubControlVolumeFace>
static constexpr bool hasVelocityInSpatialParams()
{ return Dune::Std::is_detected<HasVelocityInSpatialParams, Problem, SubControlVolumeFace>::value; }
}

/*!
 * \ingroup Fluidmatrixinteractions
 * \brief Velocity-dependent longitudinal/transverse dispersion model.
 *
 * The model reconstructs a local face velocity, assigns longitudinal and
 * transverse dispersivities for the current case, and returns the directional
 * dispersion matrix required by the Box flux calculation.
 */
template<class TypeTag>
class ScheideggersDispersionTensor
{
    using Problem = GetPropType<TypeTag, Properties::Problem>;
    using GridGeometry = GetPropType<TypeTag, Properties::GridGeometry>;
    using FVElementGeometry = typename GridGeometry::LocalView;
    using SubControlVolumeFace = typename GridGeometry::SubControlVolumeFace;
    using ElementVolumeVariables = typename GetPropType<TypeTag, Properties::GridVolumeVariables>::LocalView;

    using FluidSystem = GetPropType<TypeTag, Properties::FluidSystem>;
    using Scalar = GetPropType<TypeTag, Properties::Scalar>;
    using GridView = typename GetPropType<TypeTag, Properties::GridGeometry>::GridView;
    static const int dimWorld = GridView::dimensionworld;
    using DimWorldMatrix = Dune::FieldMatrix<Scalar, dimWorld, dimWorld>;

    using FluxVariables = GetPropType<TypeTag, Properties::FluxVariables>;
    using FluxTraits = typename Dumux::FluxTraits<FluxVariables>;
    static constexpr bool stationaryVelocityField = FluxTraits::hasStationaryVelocityField();

public:
    template <class ElementFluxVariablesCache>
    static DimWorldMatrix compositionalDispersionTensor(const Problem& problem,
                                                        const SubControlVolumeFace& scvf,
                                                        const FVElementGeometry& fvGeometry,
                                                        const ElementVolumeVariables& elemVolVars,
                                                        const ElementFluxVariablesCache& elemFluxVarsCache,
                                                        const int phaseIdx,
                                                        [[maybe_unused]] const int compIdx)
    {
        static const int dispersionMode = getParam<int>("Problem.DispersionMode", 1);

        const auto velocity = dispersionVelocity_(problem, scvf, fvGeometry, elemVolVars, elemFluxVarsCache, phaseIdx);
        Scalar longitudinalDispersivity = 0.0;
        Scalar transverseDispersivity = 0.0;

        if (dispersionMode == 1 || dispersionMode == 2)
        {
            for (auto&& scv : scvs(fvGeometry))
            {
                const auto lowerCorner = fvGeometry.geometry(scv).corner(0);
                const auto upperCorner = fvGeometry.geometry(scv).corner(3);

                // Current case-specific choice: longitudinal dispersivity is
                // twice the local cell length, transverse dispersivity is 10%
                // of the longitudinal value.
                longitudinalDispersivity = 2.0 * (upperCorner[0] - lowerCorner[0]);

                if (dispersionMode == 2)
                {
                    // Case-specific correction used in the UHS runs: scale the
                    // grid-size dispersivity with an H2/CH4 Peng-Robinson Z-ratio.
                    // TODO: Move this empirical correction into a named model with
                    // its reference, calibration range, and component pair exposed.
                    using MultiPhaseFluidSystem = typename FluidSystem::MultiPhaseFluidSystem;

                    const auto& fluidState = elemVolVars[scv].fluidState();
                    const Scalar temperature = fluidState.temperature(phaseIdx);
                    const Scalar pressure = fluidState.pressure(phaseIdx);
                    const auto zFactor = MultiPhaseFluidSystem::componentZFactors(temperature, pressure);

                    static const Scalar injectionDuration =
                        getParam<Scalar>("BoundaryConditions.InjectionDurationOp")*86400.0;

                    const Scalar h2Z = zFactor[MultiPhaseFluidSystem::H2Idx];
                    const Scalar ch4Z = zFactor[MultiPhaseFluidSystem::CH4Idx];
                    const Scalar minZ = Scalar(1e-12);
                    Scalar zRatio = problem.time() <= injectionDuration
                        ? h2Z/std::max(ch4Z, minZ)
                        : ch4Z/std::max(h2Z, minZ);

                    zRatio = std::max(Scalar(0.6), std::min(Scalar(1.6), zRatio));
                    const Scalar correctionFactor = 132.069*std::exp(-4.883*zRatio);
                    longitudinalDispersivity *= correctionFactor;
                }

                transverseDispersivity = longitudinalDispersivity / 10.0;
                break;
            }
        }
        else if (dispersionMode != 0)
        {
            // TODO: Implement additional dispersion modes as separate, documented models.
            DUNE_THROW(Dune::InvalidStateException, "Unsupported Problem.DispersionMode " << dispersionMode);
        }

        const std::array<Scalar,2> dispersivity = {longitudinalDispersivity, transverseDispersivity};
        return scheideggerTensor_(dispersivity, velocity);
    }

    template <class ElementFluxVariablesCache>
    static DimWorldMatrix thermalDispersionTensor(const Problem& problem,
                                                  const SubControlVolumeFace& scvf,
                                                  const FVElementGeometry& fvGeometry,
                                                  const ElementVolumeVariables& elemVolVars,
                                                  const ElementFluxVariablesCache& elemFluxVarsCache,
                                                  const int phaseIdx)
    {
        // Thermal dispersion keeps the standard spatial-parameter dispersivities.
        auto velocity = dispersionVelocity_(problem, scvf, fvGeometry, elemVolVars, elemFluxVarsCache, phaseIdx);
        std::array<Scalar,2> dispersivity = problem.spatialParams().dispersionAlphas(scvf.center(), phaseIdx);

        return scheideggerTensor_(dispersivity, velocity);
    }

private:

    template <class ElementFluxVariablesCache>
    static Dune::FieldVector<Scalar, dimWorld> dispersionVelocity_(const Problem& problem,
                                                                   const SubControlVolumeFace& scvf,
                                                                   [[maybe_unused]] const FVElementGeometry& fvGeometry,
                                                                   [[maybe_unused]] const ElementVolumeVariables& elemVolVars,
                                                                   [[maybe_unused]] const ElementFluxVariablesCache& elemFluxVarsCache,
                                                                   const int phaseIdx)
    {
        // Reconstruct the local face velocity used to orient hydrodynamic dispersion.
        Dune::FieldVector<Scalar, dimWorld> velocity(0.0);
        if constexpr (stationaryVelocityField)
        {
            if constexpr (!Detail::hasVelocityInSpatialParams<Problem,SubControlVolumeFace>() )
                DUNE_THROW(Dune::NotImplemented, "\n Please provide the stationary velocity field in the spatialparams via a velocity function.");
            else
                velocity = problem.spatialParams().velocity(scvf);
        }
        else
        {
            if constexpr (FVElementGeometry::GridGeometry::discMethod == DiscretizationMethods::box)
            {
                const auto& fluxVarsCache = elemFluxVarsCache[scvf];
                const auto& shapeValues = fluxVarsCache.shapeValues();

                // Average porosity and permeability across the face.
                const auto& insideVolVars = elemVolVars[scvf.insideScvIdx()];
                const auto& outsideVolVars = elemVolVars[scvf.outsideScvIdx()];
                const Scalar insidePorosity = insideVolVars.porosity();
                const Scalar outsidePorosity = outsideVolVars.porosity();
                const Scalar averagePorosity = 0.5*(insidePorosity + outsidePorosity);
                const auto K = faceTensorAverage(insideVolVars.permeability(),
                                                 outsideVolVars.permeability(),
                                                 scvf.unitOuterNormal());

                // Box reconstruction of grad(p) - rho*g at the face.
                Dune::FieldVector<Scalar, dimWorld> gradP(0.0);
                Scalar rho(0.0);
                static const bool enableGravity = getParamFromGroup<bool>(problem.paramGroup(), "Problem.EnableGravity");
                for (auto&& scv : scvs(fvGeometry))
                {
                    const auto& volVars = elemVolVars[scv];

                    if (enableGravity)
                        rho += volVars.density(phaseIdx)*shapeValues[scv.indexInElement()][0];

                    gradP.axpy(volVars.pressure(phaseIdx), fluxVarsCache.gradN(scv.indexInElement()));
                }

                if (enableGravity)
                    gradP.axpy(-rho, problem.spatialParams().gravity(scvf.center()));

                // Current 2D implementation uses the diagonal permeability entries,
                // then converts Darcy velocity to pore velocity with average porosity.
                // TODO: Generalize this reconstruction for full anisotropic tensors.
                velocity = gradP;
                velocity[0] *= K[0][0];
                velocity[1] *= K[1][1];
                velocity[0] *= 1.0 / averagePorosity;
                velocity[1] *= 1.0 / averagePorosity;
                velocity *= -0.5 * (insideVolVars.mobility(phaseIdx) + outsideVolVars.mobility(phaseIdx));
            }
            else
                DUNE_THROW(Dune::NotImplemented, "\n Scheidegger Dispersion for compositional models without given constant velocity field is only implemented using the Box method.");
        }

        return velocity;
    }

    static DimWorldMatrix scheideggerTensor_(const std::array<Scalar,2>& dispersivity,
                                             const Dune::FieldVector<Scalar, dimWorld>& velocity)
    {
        DimWorldMatrix scheideggerTensor(0.0);

        const Scalar vNorm = velocity.two_norm();
        if (vNorm < 1e-20)
            return scheideggerTensor;

        // Directional contribution from the local velocity.
        for (int i=0; i < dimWorld; i++)
            for (int j = 0; j < dimWorld; j++)
                scheideggerTensor[i][j] = velocity[i]*velocity[j];

        scheideggerTensor /= vNorm;
        scheideggerTensor *= (dispersivity[0] - dispersivity[1]);

        // Transverse contribution on the main diagonal.
        for (int i = 0; i < dimWorld; i++)
            scheideggerTensor[i][i] += vNorm*dispersivity[1];

        return scheideggerTensor;
    }

};

} // end namespace Dumux

#endif
