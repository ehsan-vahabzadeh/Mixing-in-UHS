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
 * \copydoc Dumux::ScheideggersDispersionTensor
 */
#ifndef DUMUX_MATERIAL_FLUIDMATRIX_DISPERSIONTENSORS_SCHEIDEGGER_HH
#define DUMUX_MATERIAL_FLUIDMATRIX_DISPERSIONTENSORS_SCHEIDEGGER_HH

#include <algorithm>
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
 * \brief Scheidegger's dispersion tensor
 */
template<class TypeTag>
class ScheideggersDispersionTensor
{
    using Problem = GetPropType<TypeTag, Properties::Problem>;
    using GridGeometry = GetPropType<TypeTag, Properties::GridGeometry>;
    using FVElementGeometry = typename GridGeometry::LocalView;
    using SubControlVolumeFace = typename GridGeometry::SubControlVolumeFace;
    using ElementVolumeVariables = typename GetPropType<TypeTag, Properties::GridVolumeVariables>::LocalView;

    using Scalar = GetPropType<TypeTag, Properties::Scalar>;
    using GridView = typename GetPropType<TypeTag, Properties::GridGeometry>::GridView;
    static const int dimWorld = GridView::dimensionworld;
    using DimWorldMatrix = Dune::FieldMatrix<Scalar, dimWorld, dimWorld>;

    using FluxVariables = GetPropType<TypeTag, Properties::FluxVariables>;
    using FluidState = GetPropType<TypeTag, Properties::FluidState>;
    using SolidState = GetPropType<TypeTag, Properties::SolidState>;
    using FluidSystem = GetPropType<TypeTag, Properties::FluidSystem>;
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
                                                        const int compIdx)
    {
        DimWorldMatrix dispersionTensor(0.0);
        // static const Scalar injectionDurationOp = getParam<double>("BoundaryConditions.InjectionDurationOp")*86400;
        static const int DispersionMode = getParam<int>("Problem.DispersionMode", 1);
        // auto time = problem.time();
        // Get the velocity either from the reconstruction, or from the spatialparams
        auto velocity = dispersionVelocity_(problem, scvf, fvGeometry, elemVolVars, elemFluxVarsCache,phaseIdx);
        // std::array<Scalar,2> dispersivity  = {0,0};
        Scalar alphaL = 0.0, alphaT = 0.0;
        // Scalar Z_ratio = 0.0, DiffCoeff = 0.0;
        // Scalar Porosity = 0.0, Peclet = 0.0;
        // Scalar velocity_mag = std::sqrt(std::pow(velocity[0],2)+std::pow(velocity[1],2));
        // Scalar u_x = std::abs(velocity[0]);
        if (DispersionMode != 0 ) {
            for (auto&& scv : scvs(fvGeometry))
            {
                // const FluidState &fs = elemVolVars[scv].fluidState();
                // const SolidState &ss = elemVolVars[scv].solidState();
                // Porosity = elemVolVars[scv].porosity();
                // u_x = u_x / Porosity;
                
                auto globalpos1 = fvGeometry.geometry(scv).corner(0);
                auto globalpos2 = fvGeometry.geometry(scv).corner(3);
                // if (DispersionMode == 2 ) {
                //     alphaL = 2 * (globalpos2[0] - globalpos1[0]);
                //     alphaT = 2 * (globalpos2[1] - globalpos1[1]);
                //     // auto Phi = FluidSystem::MixingFluidSystem::Fugacity_Coefficient(fs);
                //     auto Z = FluidSystem::MixingFluidSystem::Z_factor(fs);
                //     auto DiffCoeff = FluidSystem::MixingFluidSystem::binaryDiffusionCoefficient(fs,phaseIdx,1,2);
                //     // Phi_ratio = Phi[1]/Phi[2];
                //     if (time <= injectionDurationOp)
                //         Z_ratio = Z[2]/Z[1];
                //     else if (time > injectionDurationOp)
                //         Z_ratio = Z[1]/Z[2];
                //     // Peclet = velocity_mag * 2*(globalpos2[0] - globalpos1[0]) / DiffCoeff; 
                //     Scalar log_ux = log10(u_x); 
                //     Scalar CF = 0;
                //     // if (log_Pe <= 0 || Peclet < 5)
                //     if (Z_ratio < 0.6)
                //         Z_ratio = 0.6;
                //     else if (Z_ratio > 1.6)
                //         Z_ratio = 1.6;

                //     CF = 132.069 * exp(-4.883 * Z_ratio);
                //     // if (u_x == 0 || u_x< 5.5e-5 || u_x > 1.0e-2 || Z_ratio > 1.6 || Z_ratio < 0.6)
                //     //     CF = 0;
                //     // else  
                //     //     CF = 132.069 * exp(-4.883 * Z_ratio);

                //     // if(CF > 0)
                //     alphaL = alphaL * CF;
                //     alphaT = alphaL /10.0;
                //     if(CF > 3)
                //         Scalar AAAAA=1;
                // }
                if (DispersionMode == 1) {
                    // dispersivity = problem.spatialParams().dispersionTensor(globalpos1, phaseIdx, compIdx);
                    alphaL = 2 * (globalpos2[0] - globalpos1[0]);
		    //alphaL = 1;
                    alphaT = alphaL / 10.0;
                    // alphaT = 2 * (globalpos2[1] - globalpos1[1]);
                }
                
                break;
            }
            
        }
        
        
        std::array<Scalar,2> dispersivity  = {alphaL,alphaT};
        
        // collect the dispersion alphas at this location
       

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
        DimWorldMatrix dispersionTensor(0.0);

        // Get the velocity either from the reconstruction, or from the spatialparams
        auto velocity = dispersionVelocity_(problem, scvf, fvGeometry, elemVolVars, elemFluxVarsCache, phaseIdx);

        // collect the dispersion alphas at this location
        std::array<Scalar,2> dispersivity = problem.spatialParams().dispersionAlphas(scvf.center(), phaseIdx); //TODO: fix this?

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
        // Calculate Darcy's velocity
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

                // get inside and outside permeability tensors and calculate the harmonic mean
                const auto& insideVolVars = elemVolVars[scvf.insideScvIdx()];
                const auto& outsideVolVars = elemVolVars[scvf.outsideScvIdx()];
                Scalar PHI_I = insideVolVars.porosity();
                Scalar PHI_J = outsideVolVars.porosity();
                Scalar PHI_average = 0.5*(PHI_I+PHI_J);
                const auto K = faceTensorAverage(insideVolVars.permeability(),
                                                 outsideVolVars.permeability(),
                                                 scvf.unitOuterNormal());

                // evaluate gradP - rho*g at integration point
                Dune::FieldVector<Scalar, dimWorld> gradP(0.0);
                Scalar rho(0.0);
                static const bool enableGravity = getParamFromGroup<bool>(problem.paramGroup(), "Problem.EnableGravity");
                for (auto&& scv : scvs(fvGeometry))
                {
                    const auto& volVars = elemVolVars[scv];

                    if (enableGravity)
                        rho += volVars.density(phaseIdx)*shapeValues[scv.indexInElement()][0];
                    // the global shape function gradient
                    gradP.axpy(volVars.pressure(phaseIdx), fluxVarsCache.gradN(scv.indexInElement()));
                }

                if (enableGravity)
                    gradP.axpy(-rho, problem.spatialParams().gravity(scvf.center()));

                // if (std::abs(gradP[0]) > 1e-3)
                //     Scalar AAA = 0.0;
            //    static const Scalar upwindWeight = getParamFromGroup<Scalar>(elemVolVars.gridVolVars().problem().paramGroup(), "Flux.UpwindWeight");

                
                velocity = gradP;
                using std::signbit;
                // if (signbit(velocity[0])){
                //     velocity[0] *=  1.0/(upwindWeight*PHI_J+ (1.0 - upwindWeight)*PHI_I);
                //     velocity[0] *=  (upwindWeight*outsideVolVars.mobility(phaseIdx)+ (1.0 - upwindWeight)*insideVolVars.mobility(phaseIdx));
                // }else{
                //     velocity[0] *=  1.0/(upwindWeight*PHI_I+ (1.0 - upwindWeight)*PHI_J);
                //     velocity[0] *=  (upwindWeight*insideVolVars.mobility(phaseIdx)+ (1.0 - upwindWeight)*outsideVolVars.mobility(phaseIdx));
                // }
                // if (signbit(velocity[1])){
                //     velocity[1] *=  1.0/(upwindWeight*PHI_J+ (1.0 - upwindWeight)*PHI_I);
                //     velocity[1] *=  -1.0*(upwindWeight*outsideVolVars.mobility(phaseIdx)+ (1.0 - upwindWeight)*insideVolVars.mobility(phaseIdx));
                // }else{
                //     velocity[1] *=  1.0/(upwindWeight*PHI_I+ (1.0 - upwindWeight)*PHI_J);
                //     velocity[1] *= -1.0* (upwindWeight*insideVolVars.mobility(phaseIdx)+ (1.0 - upwindWeight)*outsideVolVars.mobility(phaseIdx));
                // }
                velocity[0] *= K[0][0];
                velocity[1] *= K[1][1];
                // velocity *= K;
                // velocity[0] =std::abs(velocity[0]);velocity[1] =std::abs(velocity[1]);
                velocity[0] *= 1.0 / PHI_average;
                velocity[1] *= 1.0 / PHI_average;
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

        //matrix multiplication of the velocity at the interface: vv^T
        for (int i=0; i < dimWorld; i++)
            for (int j = 0; j < dimWorld; j++)
                scheideggerTensor[i][j] = velocity[i]*velocity[j];

        //normalize velocity product --> vv^T/||v||, [m/s]
        Scalar vNorm = velocity.two_norm();

        scheideggerTensor /= vNorm;
        if (vNorm < 1e-20)
            scheideggerTensor = 0;

        //multiply with dispersivity difference: vv^T/||v||*(alphaL - alphaT), [m^2/s] --> alphaL = longitudinal disp., alphaT = transverse disp.
        scheideggerTensor *= (dispersivity[0] - dispersivity[1]);

        //add ||v||*alphaT to the main diagonal:vv^T/||v||*(alphaL - alphaT) + ||v||*alphaT, [m^2/s]
        for (int i = 0; i < dimWorld; i++)
            scheideggerTensor[i][i] += vNorm*dispersivity[1];

        return scheideggerTensor;
    }

};

} // end namespace Dumux

#endif

