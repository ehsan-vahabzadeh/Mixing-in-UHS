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
 * \ingroup TwoPNCBioGeoTest
 * \brief Problem for modeling biogeochemical reactions during Underground Hydrogen Storage
 */

#include <dumux/common/boundarytypes.hh>
#include <dumux/common/properties.hh>
#include <dumux/common/parameters.hh>
#include <dumux/common/numeqvector.hh>
#include <numeric>
#include <dumux/common/metadata.hh>
#include <dumux/discretization/extrusion.hh>
#include <dumux/porousmediumflow/problem.hh>

#include <dumux/discretization/evalgradients.hh>
#include <dumux/io/json/json.hpp>

namespace Dumux
{

    /*!
     * \ingroup TwoPNCBioGeoTest
     * \brief Problem for modeling biogeochemical reactions during Underground Hydrogen Storage
     *
     * To run the simulation execute the following line in shell:
     * <tt>appl_2pncgeobio_biogeochemical_tpfa</tt>
     */
    template <class TypeTag>
    class mixingProblem : public PorousMediumFlowProblem<TypeTag>
    {
        using ParentType = PorousMediumFlowProblem<TypeTag>;
        using GridView = typename GetPropType<TypeTag, Properties::GridGeometry>::GridView;
        using GridGeometry = GetPropType<TypeTag, Properties::GridGeometry>;
        using Scalar = GetPropType<TypeTag, Properties::Scalar>;
        using FluidSystem = GetPropType<TypeTag, Properties::FluidSystem>;

        using ModelTraits = GetPropType<TypeTag, Properties::ModelTraits>;
        using Indices = typename ModelTraits::Indices;
        using SolidSystem = GetPropType<TypeTag, Properties::SolidSystem>;

        // primary variable indices
        enum
        {
            pressureIdx = Indices::pressureIdx,
            switchIdx = Indices::switchIdx
        };

        // phase presence
        enum
        {
            wPhaseOnly = Indices::firstPhaseOnly,
            nPhaseOnly = Indices::secondPhaseOnly,
            bothPhases = Indices::bothPhases
        };

        // equation indices
        enum
        {
            numComponents = FluidSystem::numComponents,

            contiH2OEqIdx = Indices::conti0EqIdx + FluidSystem::H2OIdx,
            contiN2EqIdx = Indices::conti0EqIdx + FluidSystem::N2Idx,
            contiCO2EqIdx = Indices::conti0EqIdx + FluidSystem::CO2Idx,
            contiH2EqIdx = Indices::conti0EqIdx + FluidSystem::H2Idx,
            contiCH4EqIdx = Indices::conti0EqIdx + FluidSystem::CH4Idx,
        };

        // phase indices
        enum
        {
            gasPhaseIdx = FluidSystem::gasPhaseIdx,
            liquidPhaseIdx = FluidSystem::liquidPhaseIdx,

            H2OIdx = FluidSystem::H2OIdx,
            N2Idx = FluidSystem::N2Idx,
            CO2Idx = FluidSystem::CO2Idx,
            H2Idx = FluidSystem::H2Idx,
            CH4Idx = FluidSystem::CH4Idx,
        };


        using PrimaryVariables = GetPropType<TypeTag, Properties::PrimaryVariables>;
        using GridVariables = GetPropType<TypeTag, Properties::GridVariables>;
        using ElementVolumeVariables = typename GridVariables::GridVolumeVariables::LocalView;
        using NumEqVector = Dumux::NumEqVector<PrimaryVariables>;
        using ElementFluxVariablesCache = typename GridVariables::GridFluxVariablesCache::LocalView;
        using FluxVariables = GetPropType<TypeTag, Properties::FluxVariables>;
        using BoundaryTypes = Dumux::BoundaryTypes<GetPropType<TypeTag, Properties::ModelTraits>::numEq()>;
        using Element = typename GridView::template Codim<0>::Entity;
        using GlobalPosition = typename Element::Geometry::GlobalCoordinate;
        using FVElementGeometry = typename GetPropType<TypeTag, Properties::GridGeometry>::LocalView;
        using SubControlVolumeFace = typename FVElementGeometry::SubControlVolumeFace;
        using SubControlVolume = typename FVElementGeometry::SubControlVolume;
        using FluidState = GetPropType<TypeTag, Properties::FluidState>;
        using SolidState = GetPropType<TypeTag, Properties::SolidState>;
        using ElementIterator = typename GridView::template Codim<0>::Iterator;
        using SolutionVector = GetPropType<TypeTag, Properties::SolutionVector>;
        using VolumeVariables = GetPropType<TypeTag, Properties::VolumeVariables>;
        using ElementGeometry = typename GridGeometry::LocalView;
        using TimeLoopPtr = std::shared_ptr<TimeLoop<Scalar>>;

        using GridVariablesPtr = std::shared_ptr<GridVariables>;
        GridVariablesPtr gridVariables_;
        enum
        {
            dimWorld = GridView::dimensionworld
        };
        using VelocityOutputType = Dumux::VelocityOutput<GridVariables>;
        using VelocityOutput = VelocityOutputType;
        using Dimension_vector = Dune::FieldVector<Scalar, dimWorld>;
        using Extrusion = Extrusion_t<GridGeometry>;
        //! Property that defines whether mole or mass fractions are used
        static constexpr bool useMoles = ModelTraits::useMoles();
        using DimWorldMatrix = Dune::FieldMatrix<Scalar, dimWorld, 1>;
    public:
        mixingProblem(std::shared_ptr<const GridGeometry> gridGeometry)
            : ParentType(gridGeometry), 
            gridVariables_(nullptr)
        {
            if (useMoles)
                std::cout << "problem uses mole-fractions" << std::endl;
            else
                std::cout << "problem uses mass-fractions" << std::endl;

            if (getParam<bool>("Problem.EnableGravity", true))
                // gravity_        = {0, 0, -9.81};
                gravity_ = {0, -9.81};
            name_ = getParam<std::string>("Problem.Name");
            enableGravity = getParam<bool>("Problem.EnableGravity", true);
            permeability_.resize(gridGeometry->numDofs());
            initializeOutput();
            CELLS_VEC = getParam<Dimension_vector>("Grid.Cells");
            Upper_Right = getParam<Dimension_vector>("Grid.UpperRight");
            Lower_Left = getParam<Dimension_vector>("Grid.LowerLeft");
            X_max = Upper_Right[0];
            X_min = Lower_Left[0];
            Y_max = Upper_Right[1];
            Y_min = Lower_Left[1];
            // Z_max=this->gridGeometry().bBoxMax()[2];
            // Z_min=this->gridGeometry().bBoxMin()[2];
            Delta_x = (X_max - X_min);
            Delta_x = Delta_x / CELLS_VEC[0];
            Delta_y = (Y_max - Y_min);
            Delta_y = Delta_y / CELLS_VEC[1];
            WELL_X = (X_max - X_min)/2;
             
        }
        const GridVariables& getGridVariables() const {
                return *gridVariables_;
        }
        // double get_time_check() const {return time_check;}
        // void set_time_check(Scalar newValue) const {time_check = newValue;}
        // void LoadGridVariables(GridVariables &gridVariables) { gridvariables_ = gridVariables; } // Public setter method for time_step
        /*!
         * \brief Returns the problem name
         *
         * This is used as a prefix for files generated by the simulation.
         */
        const std::string &name() const
        {
            return name_;
        }

        template<class ElementSolution>
        Scalar extrusionFactor_sub(const Element &element,
                            const SubControlVolume &scv,
                            const ElementSolution& elemSol) const
        {
            // const auto eIdx = this->gridGeometry().elementMapper().index(element);
            // auto globalPos = element.geometry().center();
            auto globalPos_scv = scv.center();
            // return 1;
            return M_PI * globalPos_scv[0] * 2;
        }
        /*!
         * \brief Evaluates the boundary conditions for a Neumann
         *        boundary segment in dependency on the current solution.
         *
         * \param element The finite element
         * \param fvGeometry The finite volume geometry of the element
         * \param elemVolVars All volume variables for the element
         * \param elemFluxVarsCache Flux variables caches for all faces in stencil
         * \param scvf The sub-control volume facefalse
         *
         * This method is used for cases, when the Neumann condition depends on the
         * solution and requires some quantities that are specific to the fully-implicit method.
         * The \a values store the mass flux of each phase normal to the boundary.
         * Negative values indicate an inflow.
         */
        NumEqVector neumann(const Element &element,
                            const FVElementGeometry &fvGeometry,
                            const ElementVolumeVariables &elemVolVars,
                            const ElementFluxVariablesCache &elemFluxVarsCache,
                            const SubControlVolumeFace &scvf) const
        {   
            NumEqVector values(0.0);
            // return values;

            const auto &globalPos = scvf.ipGlobal();
            const auto& volVars = elemVolVars[scvf.insideScvIdx()];
            Scalar Time = this->time();
            NumEqVector injectionComposition_(0.0);
            DimWorldMatrix molardensity(0.0), MW(0.0), Mobility(0.0);
            static const Scalar cylcesDev            = getParam<double>("BoundaryConditions.CyclesDev");
            static const Scalar injectionDurationDev = getParam<double>("BoundaryConditions.InjectionDurationDev")*86400;
            static const Scalar idleDurationDev     = getParam<double>("BoundaryConditions.IdleDurationDev")*86400;
            static const Scalar developmentDuration = cylcesDev*(injectionDurationDev+idleDurationDev);
            static const Scalar idleDurationOp     = getParam<double>("BoundaryConditions.IdleDurationOp")*86400;
            static const Scalar injectionDurationOp = getParam<double>("BoundaryConditions.InjectionDurationOp")*86400;
            static const Scalar extractionDurationOp = getParam<double>("BoundaryConditions.ExtractionDurationOp")*86400;
            injectionComposition_[H2Idx]            = getParam<double>("BoundaryConditions.HydrogenInjectionConcentration");
            injectionComposition_[CO2Idx]            = 1 - getParam<double>("BoundaryConditions.HydrogenInjectionConcentration");
            double inj_rate_dev                     = getParam<double>("BoundaryConditions.InjectionRateDev");
            const int cycleNumberOp                 = std::floor((Time - developmentDuration)/(injectionDurationOp+extractionDurationOp + idleDurationOp));
            const Scalar localTimeInCycle           = Time - developmentDuration - cycleNumberOp*(injectionDurationOp + extractionDurationOp + idleDurationOp);
            double inj_rate_Op = getParam<double>("BoundaryConditions.InjectionRateOp", 0.0);
            double Extractionrate_ = getParam<double>("BoundaryConditions.ProductionRate", 0.0);
            double inj_interval = getParam<double>("BoundaryConditions.Well_Height", 0.0);


            if ((globalPos[0] < X_min + eps_) && (globalPos[1] - Y_min >= Y_max - inj_interval) && (Time < localTimeInCycle))
            // if ((globalPos[1] > Y_max - eps_)  && (Time < localTimeInCycle))
            {
                const int cycleNumber = std::floor(Time/(injectionDurationDev+idleDurationDev));
                const Scalar localTimeInCycle = Time - cycleNumber*(injectionDurationDev+idleDurationDev);
                if(localTimeInCycle <= injectionDurationDev){
                    // values[CO2Idx] = (1-injectionComposition_[CO2Idx]) * inj_rate;
                    for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                    {
                        // values[compIdx] = injectionComposition_[compIdx] * inj_rate_dev / FluidSystem::MixingFluidSystem::molarMass(compIdx);
                        values[compIdx] = injectionComposition_[compIdx] * inj_rate_dev ;
                    }   
                }  
            }
            if ((globalPos[0] < X_min + eps_) && (globalPos[1] - Y_min >= Y_max - inj_interval) && (Time >= developmentDuration))
            // if ((globalPos[1] > Y_max - eps_) && (Time >= developmentDuration))
            {
                if(localTimeInCycle < injectionDurationOp){
                    for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                    {
                        // values[compIdx] = injectionComposition_[compIdx] * inj_rate_Op / FluidSystem::MixingFluidSystem::molarMass(compIdx); 
                        values[compIdx] = injectionComposition_[compIdx] * inj_rate_Op;    
                    }
                }
                if (localTimeInCycle > injectionDurationOp + idleDurationOp ){
                    for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                    {
                        // Mobility_Gas [compIdx] = volVars.mobility(gasPhaseIdx)*volVars.moleFraction(gasPhaseIdx, compIdx);
                        // Mobility_Liq [compIdx] = volVars.mobility(liquidPhaseIdx)*volVars.moleFraction(liquidPhaseIdx, compIdx);
                        MW[liquidPhaseIdx] += volVars.moleFraction(liquidPhaseIdx, compIdx) * FluidSystem::MixingFluidSystem::molarMass(compIdx);
                        MW[gasPhaseIdx] += volVars.moleFraction(gasPhaseIdx, compIdx) * FluidSystem::MixingFluidSystem::molarMass(compIdx);
                    }
                    // Scalar Total_Mobility_Gas = 0, Total_Mobility_Liq = 0;
                    // for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                    // {
                    //         Total_Mobility_Gas += Mobility_Gas[compIdx];
                    //         Total_Mobility_Liq += Mobility_Liq[compIdx];
                    // }

                    for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                    {
                        Scalar X_GAS = volVars.moleFraction(gasPhaseIdx, compIdx);
                        Scalar X_LIQ = volVars.moleFraction(liquidPhaseIdx, compIdx);
                        Mobility [gasPhaseIdx] = volVars.mobility(gasPhaseIdx);
                        Mobility [liquidPhaseIdx] = volVars.mobility(liquidPhaseIdx);
                        // values[compIdx] = ((Extractionrate_)*(X_LIQ*Mobility[liquidPhaseIdx]/(preMobility_[liquidPhaseIdx]+preMobility_[gasPhaseIdx])) + (Extractionrate_)*(X_GAS*Mobility[gasPhaseIdx]/(preMobility_[liquidPhaseIdx]+preMobility_[gasPhaseIdx])));
                        values[compIdx] = ((Extractionrate_)*(X_LIQ*Mobility[liquidPhaseIdx]/(Mobility[liquidPhaseIdx]+Mobility[gasPhaseIdx])) + (Extractionrate_)*(X_GAS*Mobility[gasPhaseIdx]/(Mobility[liquidPhaseIdx]+Mobility[gasPhaseIdx])));
                        // values[compIdx] = (Extractionrate_/(MW[gasPhaseIdx]))*(Mobility_Gas[compIdx]/(Total_Mobility_Liq+Total_Mobility_Gas));
                    }
                }
            }
            if ((globalPos[0] > X_max - eps_))
            {

            //     // set a fixed pressure on the right side of the domain
            //     auto init_val = initial_(globalPos);
            //     Scalar phaseFlux = 0, phaseFluxn = 0;
            //     static const Scalar dirichletPressure = init_val[0];
            //     const auto& volVars = elemVolVars[scvf.insideScvIdx()];
            //     const auto& ipGlobal = scvf.ipGlobal();
            //     auto d = ipGlobal - element.geometry().center();
            //     d /= d.two_norm2();
            //     const auto tij = vtmv(scvf.unitOuterNormal(), volVars.permeability(), d);
            //     for (int phaseIdx = 0; phaseIdx < 2; ++phaseIdx)
            //     {
            //         auto upwindTerm = useMoles ? volVars.molarDensity(phaseIdx) : volVars.density(phaseIdx);
            //         upwindTerm *= volVars.mobility(phaseIdx);
                    
            //         if (phaseIdx == 0)
            //         {
            //             phaseFlux = -1.0*upwindTerm*tij*(dirichletPressure - volVars.pressure(phaseIdx));
            //         }
            //         else if (phaseIdx == 1)
            //         {
            //             phaseFluxn = -1.0*upwindTerm*tij*(dirichletPressure + volVars.capillaryPressure() - volVars.pressure(phaseIdx));
            //         }
            //     }
            //     for (int compIdx = 0; compIdx < numComponents; ++compIdx)
            //     {
            //         values[compIdx] = ((phaseFluxn * volVars.moleFraction(gasPhaseIdx, compIdx)) +
            //                            (phaseFlux * volVars.moleFraction(liquidPhaseIdx, compIdx))) /
            //                           (1);
            //         // values[compIdx] = ((phaseFluxn*volVars.moleFraction(gasPhaseIdx, compIdx))+
            //         // (phaseFlux*volVars.moleFraction(liquidPhaseIdx, compIdx))) / (volVars.mobility(0)+volVars.mobility(1));
            //     }
                
                // set a fixed pressure on the right side of the domain
                GlobalPosition dirichletPressure(0.0);
                auto init_val = initial_(globalPos);
                const auto &volVars = elemVolVars[scvf.insideScvIdx()];
                const auto &fluxVarsCache = elemFluxVarsCache[scvf];
                dirichletPressure[0] = init_val[0];
                dirichletPressure[1] = dirichletPressure[0] + volVars.capillaryPressure();
                // evaluate the pressure gradient
                GlobalPosition gradP(0.0), gradPn(0.0);
                for (int phaseIdx = 0; phaseIdx < 2; ++phaseIdx)
                {
                    for (const auto &scv : scvs(fvGeometry))
                    {
                        const auto xIp = scv.dofPosition()[0];
                        auto tmp = fluxVarsCache.gradN(scv.localDofIndex());
                        tmp *= xIp > X_max - eps_ ? dirichletPressure[phaseIdx]
                                                  : elemVolVars[scv].pressure(phaseIdx);
                        if (phaseIdx == 0)
                        {
                            gradP += tmp;
                        }
                        else if (phaseIdx == 1)
                        {
                            gradPn += tmp;
                        }
                    }
                }
                auto phaseFlux = vtmv(scvf.unitOuterNormal(), volVars.permeability(), gradP);
                auto phaseFluxn = vtmv(scvf.unitOuterNormal(), volVars.permeability(), gradPn);
            
                phaseFlux *= -1*volVars.mobility(0);
                phaseFluxn *= -1*volVars.mobility(1);
                phaseFlux *= useMoles ? volVars.molarDensity(0) : volVars.density(0);
                phaseFluxn *= useMoles ? volVars.molarDensity(1) : volVars.density(1);

                for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                {
                    values[compIdx] = ((phaseFluxn * volVars.moleFraction(gasPhaseIdx, compIdx)) +
                                       (phaseFlux * volVars.moleFraction(liquidPhaseIdx, compIdx))) /
                                      (1);
                    // values[compIdx] = ((phaseFluxn*volVars.moleFraction(gasPhaseIdx, compIdx))+
                    // (phaseFlux*volVars.moleFraction(liquidPhaseIdx, compIdx))) / (volVars.mobility(0)+volVars.mobility(1));
                }
            }


            return values;
        }
        void postTimeStep(const SolutionVector &curSol,
                          const SolutionVector &pastSol,
                          const GridVariables &gridVariables,
                          const Scalar timeStepSize,
                          std::shared_ptr<const GridGeometry> fvGridGeometry)
        {   
            Scalar num_x = CELLS_VEC[0],num_grid = CELLS_VEC[0] * CELLS_VEC[1];
            Scalar t, dt, volume(0.0), numberOfCells(0.0);
            NumEqVector flow1(0.0);
            NumEqVector inventory(0.0), inventoryPastSol(0.0), materialBalanceError(0.0), inventory_error(0.0);
            Scalar averageReservoirPressure(0.0);
            GAS_MAT.resize(num_grid);LIQ_MAT.resize(num_grid);
            GAS_MASS_MAT.resize(num_grid);LIQ_MASS_MAT.resize(num_grid);
            MASS_MAT.resize(num_grid);
            
            Scalar X_ID = 0, Z_ID = 0, Grid_ID = 0;
            for (auto& row : GAS_MAT){row.resize(5+numComponents);} 
            for (auto& row : LIQ_MAT){row.resize(numComponents);} 
            for (auto& row : GAS_MASS_MAT){row.resize(numComponents);}
            for (auto& row : LIQ_MASS_MAT){row.resize(numComponents);}
            for (auto& row : MASS_MAT){row.resize(numComponents);}
            // fill(GAS_MAT.begin(), GAS_MAT.end(), 0);    

            t = this->time();
            Scalar Time = t;
            dt = this->timeStepSize();
            mobilityPostLiq = 0;
            mobilityPostGas = 0;
            NumEqVector values_inj(0.0), values_prod(0.0), outflow(0.0);
            
            for (const auto &element : elements(this->gridGeometry().gridView(), Dune::Partitions::interior))
            {
                auto fvGeometry = localView(*fvGridGeometry);
                fvGeometry.bind(element);

                // auto fvGeometry = localView(this->gridGeometry());
                // fvGeometry.bindElement(element);
                auto globalPos = element.geometry().center();
                for (auto compIdx = 0; compIdx < numComponents; ++compIdx)
                    {
                        if (compIdx < numComponents){
                            MASS_MAT[Grid_ID][compIdx] = 0.0;
                            GAS_MASS_MAT[Grid_ID][compIdx] = 0.0;
                            LIQ_MASS_MAT[Grid_ID][ compIdx] = 0.0;
                            GAS_MAT[Grid_ID][5 + compIdx] = 0.0;
                            LIQ_MAT[Grid_ID][compIdx] = 0.0;
                        }else{
                            GAS_MAT[Grid_ID][5 + compIdx] = 0.0;
                            LIQ_MAT[Grid_ID][compIdx] = 0.0;
                            MASS_MAT[Grid_ID][compIdx] = 0.0;
                        }                    
                    }
                GAS_MAT[Grid_ID][0] = globalPos[0];
                GAS_MAT[Grid_ID][1] = globalPos[1];
                GAS_MAT[Grid_ID][2] = Grid_ID;
                GAS_MAT[Grid_ID][3] = X_ID;
                GAS_MAT[Grid_ID][4] = Z_ID;
                auto elemVolVars = localView(gridVariables.curGridVolVars());
                elemVolVars.bindElement(element, fvGeometry, curSol);
                auto prevElemVolVars = localView(gridVariables.prevGridVolVars());
                prevElemVolVars.bindElement(element, fvGeometry, pastSol);

                const auto elemSol = elementSolution(element, curSol, this->gridGeometry());
                const auto elemSolPast = elementSolution(element, pastSol, this->gridGeometry());
                auto elemFluxVarsCache = localView(gridVariables.gridFluxVarsCache());
                elemVolVars.bind(element, fvGeometry, curSol);
                elemFluxVarsCache.bind(element, fvGeometry, elemVolVars);

                for (auto &&scv : scvs(fvGeometry))
                {
                    const FluidState &fs = elemVolVars[scv].fluidState();
                    const FluidState &fsOld = prevElemVolVars[scv].fluidState();
                    // Scalar extrusion_  = extrusionFactor_sub(element, scv, elemSol);
                    Scalar extrusion_ = Extrusion::volume(fvGeometry, scv);
                    // Scalar extrusion_ = elemVolVars[scv].extrusionFactor();
                    VolumeVariables volVars, volVarsPast;
                    volVars.update(elemSol, *this, element, scv);
                    volVarsPast.update(elemSolPast, *this, element, scv);

                    for (auto compIdx = 0; compIdx < numComponents; ++compIdx)
                    {
                        if (compIdx < numComponents){
                            MASS_MAT[Grid_ID][compIdx] += volVars.porosity() * extrusion_ * ((fs.saturation(gasPhaseIdx) * fs.molarDensity(gasPhaseIdx) * fs.moleFraction(gasPhaseIdx, compIdx) + fs.saturation(liquidPhaseIdx) * fs.molarDensity(liquidPhaseIdx) * fs.moleFraction(liquidPhaseIdx, compIdx)));   
                            GAS_MASS_MAT[Grid_ID][compIdx] += fs.molarDensity(gasPhaseIdx) * fs.moleFraction(gasPhaseIdx, compIdx) * volVars.porosity() * scv.volume()* extrusion_ * fs.saturation(gasPhaseIdx) ;
                            LIQ_MASS_MAT[Grid_ID][ compIdx] += fs.molarDensity(liquidPhaseIdx) * fs.moleFraction(liquidPhaseIdx, compIdx) * volVars.porosity() * scv.volume()* extrusion_ * fs.saturation(liquidPhaseIdx) ;
                            GAS_MAT[Grid_ID][5 + compIdx] += fs.moleFraction(gasPhaseIdx, compIdx);
                            LIQ_MAT[Grid_ID][compIdx] += fs.moleFraction(liquidPhaseIdx, compIdx);
                        }                   
                    }
                    for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                    {
                        
                    inventory[compIdx] += volVars.porosity() * extrusion_  * ((fs.saturation(gasPhaseIdx) * fs.molarDensity(gasPhaseIdx) * fs.moleFraction(gasPhaseIdx, compIdx) + fs.saturation(liquidPhaseIdx) * fs.molarDensity(liquidPhaseIdx) * fs.moleFraction(liquidPhaseIdx, compIdx)));
                    inventoryPastSol[compIdx] += volVarsPast.porosity() * extrusion_  * ((fsOld.saturation(gasPhaseIdx) * fsOld.molarDensity(gasPhaseIdx) * fsOld.moleFraction(gasPhaseIdx, compIdx) + fsOld.saturation(liquidPhaseIdx) * fsOld.molarDensity(liquidPhaseIdx) * fsOld.moleFraction(liquidPhaseIdx, compIdx)));
                    }
                    GAS_MAT[Grid_ID][5 + numComponents-1] = volVars.permeability()[0][0];
                    averageReservoirPressure += fs.pressure(gasPhaseIdx) * scv.volume();
                    numberOfCells += 1;
                    volume += scv.volume();
                }
                Grid_ID = Grid_ID +1;
                if (X_ID < num_x - 1){
                    X_ID = X_ID + 1;
                }else{
                    X_ID = 0;
                    Z_ID = Z_ID + 1;
                }
                    

                // %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
                
                NumEqVector injectionComposition_(0.0);
                injectionComposition_[H2Idx] = 1.0;
                injectionComposition_[CO2Idx] = 0.00;
                DimWorldMatrix molardensity(0.0), MW(0.0),Mobility(0.0);
                static const Scalar cylcesDev            = getParam<double>("BoundaryConditions.CyclesDev");
                static const Scalar injectionDurationDev = getParam<double>("BoundaryConditions.InjectionDurationDev")*86400;
                static const Scalar idleDurationDev     = getParam<double>("BoundaryConditions.IdleDurationDev")*86400;
                static const Scalar developmentDuration = cylcesDev*(injectionDurationDev+idleDurationDev);
                static const Scalar idleDurationOp     = getParam<double>("BoundaryConditions.IdleDurationOp")*86400;
                static const Scalar injectionDurationOp = getParam<double>("BoundaryConditions.InjectionDurationOp")*86400;
                static const Scalar extractionDurationOp = getParam<double>("BoundaryConditions.ExtractionDurationOp")*86400;
                injectionComposition_[H2Idx]            = getParam<double>("BoundaryConditions.HydrogenInjectionConcentration");
                injectionComposition_[CO2Idx]            = 1 - getParam<double>("BoundaryConditions.HydrogenInjectionConcentration");
                double inj_rate_dev                     = getParam<double>("BoundaryConditions.InjectionRateDev");
                const int cycleNumberOp                 = std::floor((Time - developmentDuration)/(injectionDurationOp+extractionDurationOp + idleDurationOp));
                const Scalar localTimeInCycle           = Time - developmentDuration - cycleNumberOp*(injectionDurationOp + extractionDurationOp + idleDurationOp);
                double inj_rate_Op = getParam<double>("BoundaryConditions.InjectionRateOp", 0.0);
                double Extractionrate_ = getParam<double>("BoundaryConditions.ProductionRate", 0.0);
                double inj_interval = getParam<double>("BoundaryConditions.Well_Height", 0.0);
                for (auto&& scvf : scvfs(fvGeometry) )
                {   
                    const auto& scv = fvGeometry.scv(scvf.insideScvIdx());
                    VolumeVariables volVars, volVarsPast;
                    volVars.update(elemSol, *this, element, scv);
                    volVarsPast.update(elemSolPast, *this, element, scv);
                    Scalar extrusion_  = Extrusion::area(fvGeometry, scvf);
                    // if (scvf.boundary() && scvf.area() == Delta_y/2 && scvf.corner(0)[0] == X_min && scvf.corner(1)[0] == X_min)
                    if (scvf.boundary()  && scvf.area() == Delta_y/2 && scvf.center()[0] == X_min)
                    {
                        // const auto& globalPos = scvf.ipGlobal()[0];
                        // if ((globalPos[0] - Delta_x/2 < X_min + eps_) && (globalPos[1] - Y_min >= Y_max - inj_interval) && (Time < localTimeInCycle))
                        if ((scvf.center()[1] - Y_min >= Y_max - inj_interval) && (Time < localTimeInCycle))
                        {
                            const int cycleNumber = std::floor(Time/(injectionDurationDev+idleDurationDev));
                            const Scalar localTimeInCycle = Time - cycleNumber*(injectionDurationDev+idleDurationDev);
                            if(localTimeInCycle <= injectionDurationDev){
                                // values[CO2Idx] = (1-injectionComposition_[CO2Idx]) * inj_rate;
                                for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                                {
                                    
                                    // values_inj[compIdx] += injectionComposition_[compIdx] * Delta_y* inj_rate_dev / FluidSystem::MixingFluidSystem::molarMass(compIdx);
                                    values_inj[compIdx] += injectionComposition_[compIdx] * extrusion_ * inj_rate_dev;
                                }
                            }
                        }
                        // if ((globalPos[0] - Delta_x/2 < X_min + eps_) && (globalPos[1] - Y_min >= Y_max - inj_interval) && (Time >= developmentDuration))
                        if ((scvf.center()[1] - Y_min >= Y_max - inj_interval) && (Time >= developmentDuration))
                        {
                            if(localTimeInCycle < injectionDurationOp){
                                for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                                {
                                    Scalar MW_check = FluidSystem::MixingFluidSystem::molarMass(compIdx);
                                    // values_inj[compIdx] += injectionComposition_[compIdx] * Delta_y* inj_rate_Op / MW_check;    
                                    values_inj[compIdx] += injectionComposition_[compIdx] * extrusion_ * inj_rate_Op;  
                                }
                            }
                            if (localTimeInCycle > injectionDurationOp + idleDurationOp ){
                                for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                                {
                                    // Mobility_Gas [compIdx] = volVars.mobility(gasPhaseIdx)*volVars.moleFraction(gasPhaseIdx, compIdx);
                                    // Mobility_Liq [compIdx] = volVars.mobility(liquidPhaseIdx)*volVars.moleFraction(liquidPhaseIdx, compIdx);
                                    MW[liquidPhaseIdx] += volVars.moleFraction(liquidPhaseIdx, compIdx) * FluidSystem::MixingFluidSystem::molarMass(compIdx);
                                    MW[gasPhaseIdx] += volVars.moleFraction(gasPhaseIdx, compIdx) * FluidSystem::MixingFluidSystem::molarMass(compIdx);
                                }
                                // Scalar Total_Mobility_Gas = 0, Total_Mobility_Liq = 0;
                                // for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                                // {
                                //         Total_Mobility_Gas += Mobility_Gas[compIdx];
                                //         Total_Mobility_Liq += Mobility_Liq[compIdx];
                                // }

                                for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                                {
                                    Scalar X_GAS = volVars.moleFraction(gasPhaseIdx, compIdx);
                                    Scalar X_LIQ = volVars.moleFraction(liquidPhaseIdx, compIdx);
                                    Mobility [gasPhaseIdx] = volVars.mobility(gasPhaseIdx);
                                    Mobility [liquidPhaseIdx] = volVars.mobility(liquidPhaseIdx);
                                    // values_prod[compIdx] += Delta_y* ((Extractionrate_)*(X_LIQ*Mobility[liquidPhaseIdx]/(preMobility_[liquidPhaseIdx]+preMobility_[gasPhaseIdx])) + (Extractionrate_)*(X_GAS*Mobility[gasPhaseIdx]/(preMobility_[liquidPhaseIdx]+preMobility_[gasPhaseIdx])));
                                    values_prod[compIdx] +=  extrusion_ * ((Extractionrate_)*(X_LIQ*Mobility[liquidPhaseIdx]/(Mobility[liquidPhaseIdx]+Mobility[gasPhaseIdx])) + (Extractionrate_)*(X_GAS*Mobility[gasPhaseIdx]/(Mobility[liquidPhaseIdx]+Mobility[gasPhaseIdx])));
                                    // values_prod[compIdx] +=  Delta_y* 
                                    //                         ((Extractionrate_/(MW[liquidPhaseIdx]))*(X_LIQ*Mobility[liquidPhaseIdx]/(Mobility[liquidPhaseIdx]+Mobility[gasPhaseIdx])) + 
                                    //                         (Extractionrate_/(MW[gasPhaseIdx]))*(X_GAS*Mobility[gasPhaseIdx]/(Mobility[liquidPhaseIdx]+Mobility[gasPhaseIdx])));
                                }
                            }
                        }

                        if ((globalPos[0] + Delta_x/2 > X_max - eps_))
                        {
                            // set a fixed pressure on the right side of the domain
                            auto init_val = initial_(globalPos);
                            Scalar phaseFlux = 0, phaseFluxn = 0;
                            static const Scalar dirichletPressure = init_val[0];
                            const auto& volVars = elemVolVars[scvf.insideScvIdx()];
                            const auto& ipGlobal = scvf.ipGlobal();
                            auto d = ipGlobal - element.geometry().center();
                            d /= d.two_norm2();
                            const auto tij = vtmv(scvf.unitOuterNormal(), volVars.permeability(), d);
                            for (int phaseIdx = 0; phaseIdx < 2; ++phaseIdx)
                            {
                                auto upwindTerm = useMoles ? volVars.molarDensity(phaseIdx) : volVars.density(phaseIdx);
                                upwindTerm *= volVars.mobility(phaseIdx);
                                
                                if (phaseIdx == 0)
                                {
                                    phaseFlux = -1.0*upwindTerm*tij*(dirichletPressure - volVars.pressure(phaseIdx));
                                }
                                else if (phaseIdx == 1)
                                {
                                    phaseFluxn = -1.0*upwindTerm*tij*(dirichletPressure + volVars.capillaryPressure() - volVars.pressure(phaseIdx));
                                }
                            }
                            for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                            {
                                outflow[compIdx] += ((phaseFluxn * volVars.moleFraction(gasPhaseIdx, compIdx)) +
                                                (phaseFlux * volVars.moleFraction(liquidPhaseIdx, compIdx))) *
                                                Delta_y;
                                // values[compIdx] = ((phaseFluxn*volVars.moleFraction(gasPhaseIdx, compIdx))+
                                // (phaseFlux*volVars.moleFraction(liquidPhaseIdx, compIdx))) / (volVars.mobility(0)+volVars.mobility(1));
                            }
                        }
                    }
                }
                // %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            }
            const auto &comm = this->gridGeometry().gridView().comm();
            // Scalar sum_inj = std::accumulate(values_inj.begin(), values_inj.end(), 0);
            // Scalar sum_prod = std::accumulate(values_prod.begin(), values_prod.end(), 0);

            materialBalanceError = inventoryPastSol - inventory - dt * values_inj + dt * values_prod;

            // materialBalanceError = inventory + t * values_inj + t * values_prod;
            inventory_error = inventoryPastSol - inventory;
            Scalar error_sum = 0, inventory_error_sum = 0;
            for (int compIdx = 0; compIdx < numComponents; ++compIdx)
             {
                error_sum = error_sum + materialBalanceError[compIdx];
                inventory_error_sum = inventory_error_sum + inventory_error[compIdx];
            }
            std::cout << "The material balance error is: " << materialBalanceError[2] <<  std::endl;
            // std::cout << "The material balance error is: " << materialBalanceError[2] <<  std::endl;

            std::cout << "---------------------------------------------info end------------------------------------------------------------" << std::endl;

            Dumux::MetaData::Collector collector;
            if (Dumux::MetaData::jsonFileExists(name()))
                Dumux::MetaData::readJsonFile(collector, name());
            collector["time"].push_back(t);
            collector["averageReservoirPressure"].push_back(comm.sum(averageReservoirPressure) / comm.sum(volume));
            for (auto compIdx = 0; compIdx < numComponents; ++compIdx)
            {
                collector["inventory"][FluidSystem::componentName(compIdx)].push_back(comm.sum(inventory[compIdx]));
                collector["materialBalanceError"][FluidSystem::componentName(compIdx)].push_back(comm.sum(materialBalanceError[compIdx]));
                collector["InjectionValues"][FluidSystem::componentName(compIdx)].push_back(comm.sum(values_inj[compIdx]));
                collector["ProductionValues"][FluidSystem::componentName(compIdx)].push_back(comm.sum(values_prod[compIdx]));
                collector["outflow"][FluidSystem::componentName(compIdx)].push_back(comm.sum(outflow[compIdx]));
            }
            
            Dumux::MetaData::writeJsonFile(collector, name());

            // // Prepare the matrix data for JSON
            // nlohmann::json timestepData;
            // timestepData["Time"] = t;
            // timestepData["GAS_MAT"] = GAS_MAT;
            // timestepData["LIQ_MAT"] = LIQ_MAT;
            // timestepData["GAS_MASS_MAT"] = GAS_MASS_MAT;
            // timestepData["LIQ_MASS_MAT"] = LIQ_MASS_MAT;
            // timestepData["MASS_MAT"] = MASS_MAT;
            // std::string filename = "average_concentration.json";
            // // JSON object for storing the full data
            // nlohmann::json fullData;
            // // Check if the JSON file already exists
            // std::ifstream inputFile(filename);
            // if (inputFile) {
            //     // Read the existing data into fullData
            //     inputFile >> fullData;
            //     inputFile.close();
            // }
            // // Append new data
            // fullData.push_back(timestepData);

            // // Write the updated JSON data back to the file
            // std::ofstream outputFile(filename);
            // outputFile << std::setw(4) << fullData << std::endl;
            // outputFile.close();



        }

        /*!
         * \brief source term covering operation from well and geochemical reactions
         */
        NumEqVector source(const Element &element,
                           const FVElementGeometry &fvGeometry,
                           const ElementVolumeVariables &elemVolVars,
                           const SubControlVolume &scv) const
        {
            NumEqVector sourceFlow(0.0), sourceG(0.0), sourceMG(0.0), sourceSR(0.0),sourceBioMG(0.0), sourceBioSRB(0.0);
            const auto &volVars = elemVolVars[scv];
            // sourceFlow = sourceflow(element, fvGeometry, prevElemVolVars, elemVolVars, scv); // source from wells

            NumEqVector values(0.0);
            // values = sourceFlow + sourceG + sourceMG + sourceSR + sourceBioMG + sourceBioSRB;
            return values;
        }
    
        /*!
         * \brief Specifies which kind of boundary condition should be
         *        used for which equation on a given boundary segment
         *
         * \param globalPos The global position
         */
        BoundaryTypes boundaryTypesAtPos(const GlobalPosition &globalPos) const
        {
            BoundaryTypes bcTypes;
            // Scalar Time = this->time();
            // if (Time > 50.0 && Time < 51.0){
            //     bcTypes.setAllDirichlet();
            //     // set_time_check(1.0);
            //     time_check = 1;
            // }
            // else if(Time > 50.0 && globalPos[0] > X_max - eps_){
            //     bcTypes.setAllDirichlet();
                
            // } 
            // else{
            //     bcTypes.setAllNeumann();
            // }  

            bcTypes.setAllNeumann();

            // if (globalPos[0] > X_max - eps_ & globalPos[0] < X_min + eps_ && globalPos[1] < Y_min + eps_)
            // if ( globalPos[0] > X_max - eps_)
            //     bcTypes.setAllDirichlet();
            // else
            //     bcTypes.setAllNeumann();
            return bcTypes;
        }

        /*!
         * \brief Evaluates the boundary conditions for a Dirichlet boundary segment
         *
         * \param globalPos The global position
         */
        PrimaryVariables dirichletAtPos(const GlobalPosition &globalPos) const
        {
            return initial_(globalPos);
        }

        

        // Function to return the permeability for additional vtk output
        const std::vector<Scalar> &getPermeability()
        {
            return permeability_;
        }


        // Function to update the permeability for additional vtk output
        template <class SolutionVector>
        void updateVtkOutput(const SolutionVector &curSol)
        {
            for (const auto &element : elements(this->gridGeometry().gridView()))
            {
                const auto elemSol = elementSolution(element, curSol, this->gridGeometry());
                auto fvGeometry = localView(this->gridGeometry());
                fvGeometry.bindElement(element);
                for (const auto &scv : scvs(fvGeometry))
                {
                    VolumeVariables volVars;
                    volVars.update(elemSol, *this, element, scv);
                    const auto dofIdxGlobal = scv.dofIndex();
                    permeability_[dofIdxGlobal] = volVars.permeability()[0][0] / 9.86923e-16;
                }
            }
        }

        /*!
         * \brief Evaluates the initial values for a control volume.
         *
         * \param globalPos The global position
         */
        PrimaryVariables initialAtPos(const GlobalPosition &globalPos) const
        {
            return initial_(globalPos);
        }

        Scalar time() const
        {
            return timeLoop_->time();
        }

        void setTimeLoop(TimeLoopPtr timeLoop)
        {
            timeLoop_ = timeLoop;
            // timeLoop_->setCheckPoint({86400, 3 * 2.592e+6});
        }

        Scalar timeStepSize() const
        {
            return timeLoop_->timeStepSize();
        }

        const GlobalPosition &gravity() const
        {
            return gravity_;
        }

        GlobalPosition gravity_;

    private:

        /*!
         * \brief Evaluates the initial values for a control volume.
         *
         * The internal method for the initial condition
         *
         * \param globalPos The global position
         */

        PrimaryVariables initial_(const GlobalPosition &globalPos) const
        {
            PrimaryVariables values;

            
            // hydrostatic pressure
            
            Scalar pressureGasWaterContact_ = getParam<Scalar>("Initialization.PressureGWC", 100e5);
            Scalar gasWaterContact_ = getParam<Scalar>("Initialization.DepthGWC", 0);
            FluidState fs;
            fs.setMoleFraction(gasPhaseIdx, CO2Idx, 1.0); fs.setMoleFraction(gasPhaseIdx, CH4Idx, 0.0); fs.setMoleFraction(liquidPhaseIdx, H2OIdx, 1);
            const auto &fluidMatrixInteraction = this->spatialParams().fluidMatrixInteractionAtPos(globalPos);
            Scalar thresholdPressure_ = fluidMatrixInteraction.pc(1 - fluidMatrixInteraction.pcSwCurve().effToAbsParams().snr());
            fs.setPressure(liquidPhaseIdx, pressureGasWaterContact_); fs.setPressure(gasPhaseIdx, pressureGasWaterContact_+thresholdPressure_);
            // fs.density(liquidPhaseIdx); fs.density(gasPhaseIdx);
            fs.setTemperature(this->spatialParams().temperatureAtPos(globalPos));
            // Scalar densityW = fs.density(fs, liquidPhaseIdx);
            
            values.setState(bothPhases);

            Scalar pn = 0.0;
            Scalar pw = 0.0;
            Scalar Sw, pC;
            Scalar check = 1.0;
            Scalar z = globalPos[dimWorld - 1];
            Scalar densityW = 1000;//1020;
            Scalar densityG = 150;

            // while (check > 1e-12){
            //     Scalar densityW = FluidSystem::density(fs,liquidPhaseIdx); // 1020;
            //     Scalar densityG = FluidSystem::density(fs,gasPhaseIdx) ;
            //     pw = (pressureGasWaterContact_ - (densityW* gravity()[dimWorld - 1] * (gasWaterContact_ - (globalPos)[dimWorld - 1])));
            //     pn = (pressureGasWaterContact_ + thresholdPressure_ - (densityG * gravity()[dimWorld - 1] * (gasWaterContact_ - (globalPos)[dimWorld - 1])));
            //     fs.setPressure(liquidPhaseIdx, pw); fs.setPressure(gasPhaseIdx, pn);
            //     check = std::abs(densityG - FluidSystem::density(fs,gasPhaseIdx));
            // }
            
            // values[pressureIdx] = pw;
            // values[switchIdx] = 0.8;
            // if (getParam<bool>("Problem.EnableGravity", false)){
            //     values[pressureIdx] = pressureGasWaterContact_;
            //     values[switchIdx] = 1 - fluidMatrixInteraction.pcSwCurve().effToAbsParams().swr();
            //     return values;
            // }
            // Water Zone
            if (z <= gasWaterContact_)
            {
                pw = (pressureGasWaterContact_ - (densityW * gravity()[dimWorld - 1] * (gasWaterContact_ - (globalPos)[dimWorld - 1])));
                pn = pw + thresholdPressure_;

                fs.setPressure(liquidPhaseIdx, pw);
                fs.setPressure(gasPhaseIdx, pn);

                values[pressureIdx] = pw;
                values[switchIdx] = fluidMatrixInteraction.pcSwCurve().effToAbsParams().snr();
            }
            else
            {
                // transition zone_______
                // the water pressure is calculated by the hydrostativ gradient of water
                // this is only true in the transition zone, otherwise it will be overwritten
                while (check > 1e-6){
                    pw = (pressureGasWaterContact_ - (densityW * gravity()[dimWorld - 1] * (gasWaterContact_ - (globalPos)[dimWorld - 1])));
                    // pw = pressureGasWaterContact_ ;
                    fs.setPressure(liquidPhaseIdx, pw);

                    // the gas pressure is calculated by hydrostatic gradient of gas
                    //  this is true in the transition zone and the gas zone
                    pn = (pressureGasWaterContact_ + thresholdPressure_ - (densityG * gravity()[dimWorld - 1] * (gasWaterContact_ - (globalPos)[dimWorld - 1])));
                    // pn = pressureGasWaterContact_ + thresholdPressure_ ;
                    fs.setPressure(gasPhaseIdx, pn);
                    check = std::abs(densityG - FluidSystem::density(fs,gasPhaseIdx))+ std::abs(densityW - FluidSystem::density(fs,liquidPhaseIdx));
                    densityW = FluidSystem::density(fs,liquidPhaseIdx); // 1020;
                    densityG = FluidSystem::density(fs,gasPhaseIdx) ;
                    Sw = fluidMatrixInteraction.pcSwCurve().sw((pn - pw));
                }

                // setting the fluid state in the gas zone
                // for brooks and corey the if statement would never become true, therefore 1% is added
                // which means that the saturation is ver close to the residual water saturation
                if (Sw <= fluidMatrixInteraction.pcSwCurve().effToAbsParams().swr() + 0.0001)
                {
                    Sw = fluidMatrixInteraction.pcSwCurve().effToAbsParams().swr() + 0.0001;
                    values[Indices::switchIdx] = 1 - Sw;

                    // Calculating the water pressure by gas pressure minus capillary pressure
                    pC = fluidMatrixInteraction.pcSwCurve().pc(Sw);
                    pw = pn - pC;
                    fs.setPressure(liquidPhaseIdx, pw);
                    values[Indices::pressureIdx] = pw;
                }
                else
                {
                    values[pressureIdx] = pw;
                    values[switchIdx] = 1 - Sw;
                }
            }
            if (!enableGravity){
                values[pressureIdx] = pressureGasWaterContact_;
                values[switchIdx] = 1 - fluidMatrixInteraction.pcSwCurve().effToAbsParams().swr();
            }

            Scalar xgH2O = (FluidSystem::fugacityCoefficient(fs,liquidPhaseIdx,H2OIdx)* pw) / pn;
            // values[contiCO2EqIdx]  =  0.5*(1-xgH2O) * pn / (FluidSystem::fugacityCoefficient(fs,liquidPhaseIdx,CO2Idx) * pw);
            // values[contiCH4EqIdx]  =  0.5*(1-xgH2O) * pn / (FluidSystem::fugacityCoefficient(fs,liquidPhaseIdx,CH4Idx) * pw);
            // values[contiH2EqIdx]  =  0.5*(1-xgH2O) * pn / (FluidSystem::fugacityCoefficient(fs,liquidPhaseIdx,H2Idx) * pw);
            // values[contiN2EqIdx]  =  0.1198*(1-xgH2O) * pn / (FluidSystem::fugacityCoefficient(fs,liquidPhaseIdx,N2Idx) * pw);

            return values;
        }

        void initializeOutput()
        {
            Dumux::MetaData::Collector collector;
            Dumux::MetaData::writeJsonFile(collector, name());
        }

        TimeLoopPtr timeLoop_;
        Scalar temperature_;
        DimWorldMatrix preMobility_;
        Scalar mobilityPreLiq;
        Scalar mobilityPreGas;

        Scalar mobilityPostLiq;
        Scalar mobilityPostGas;

        std::vector<double> timeout;
        std::vector<double> bhpout;
        std::vector<double> averageReservoirPressureout;
        Scalar t_old = 0;
        std::vector<double> checkpoints_;
        std::vector<NumEqVector> convertedGeoout, convertedMGout, convertedSRout;
        std::vector<NumEqVector> inventoryout, materialBalanceErrorout;
        std::vector<std::string> componentsOut;
        Scalar initalPyriteContent;
        bool enableMicrobes, enableGeochemistry, enableSulfateReduction;
        
        Dimension_vector CELLS_VEC;
        Dimension_vector Upper_Right, Lower_Left;
        double Delta_z = 0.0;
        double Delta_x = 0.0;
        double Delta_y = 0.0;
        double X_max = 0.0;
        double X_min = 0;
        double Y_max = 0.0;
        double Y_min = 0.0;
        double Z_max = 0.0;
        double Z_min = 0.0;
        Scalar WELL_X =0;
        mutable Scalar well_loc = 0;
        static constexpr Scalar eps_ = 1e-6;
        mutable Scalar time_check = 50.0;
        bool enableGravity = false;
        // biomass parameters for source/sink calculations
        Scalar ca1_;
        Scalar ca2_;
        Scalar cd1_;
        Scalar dc0_;
        Scalar kmue_ ;
        Scalar f_;
        Scalar ke_;
        Scalar ks_;
        Scalar yield_;
        Scalar Initial_Biomass_fraction;
        Scalar InihibitonConstant;
        // the permeability for output
        std::vector<Scalar> permeability_;
        std::vector<std::vector<double>> GAS_MAT;
        std::vector<std::vector<double>> LIQ_MAT;
        std::vector<std::vector<double>> MASS_MAT;
        std::vector<std::vector<double>> GAS_MASS_MAT;
        std::vector<std::vector<double>> LIQ_MASS_MAT;      

        std::string name_;

    };

} // end namespace Dumux

// #endif