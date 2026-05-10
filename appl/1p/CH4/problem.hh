// -*- mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*-
// vi: set et ts=4 sw=4 sts=4:
//
// SPDX-FileCopyrightInfo: Copyright (C) DuMux Project contributors, see AUTHORS.md in root folder
// SPDX-License-Identifier: GPL-3.0-or-later
//
/**
 * \file
 * \ingroup OnePNCTests
 * \brief Definition of a problem for the 1pnc problem:
 * Component transport of nitrogen dissolved in the water phase.
 */

#ifndef DUMUX_1P2C_TEST_PROBLEM_HH
#define DUMUX_1P2C_TEST_PROBLEM_HH

#include <algorithm>
#include <cmath>
#include <iostream>

#include <dumux/common/properties.hh>
#include <dumux/common/parameters.hh>

#include <dumux/common/boundarytypes.hh>
#include <dumux/common/numeqvector.hh>
#include <dumux/porousmediumflow/problem.hh>

#include <dumux/common/metadata.hh>
#include <dumux/discretization/extrusion.hh>

#include <dumux/discretization/evalgradients.hh>
#include <dumux/io/json/json.hpp>


namespace Dumux {

/*!
 * \ingroup OnePNCTests
 * \brief Definition of a problem for the 1pnc problem:
 *  Component transport of hydrogen in the gas phase.
 *
 *
 * The model domain is specified in the input file and
 * we use homogeneous soil properties.
 * Initially, the domain is filled with pure water.
 *
 * This problem uses the \ref OnePNCModel model.
 */
template <class TypeTag>
class OnePTwoCTestProblem : public PorousMediumFlowProblem<TypeTag>
{
    using ParentType = PorousMediumFlowProblem<TypeTag>;

    using Scalar = GetPropType<TypeTag, Properties::Scalar>;
    using FluidSystem = GetPropType<TypeTag, Properties::FluidSystem>;
    using BoundaryTypes = Dumux::BoundaryTypes<GetPropType<TypeTag, Properties::ModelTraits>::numEq()>;
    using PrimaryVariables = GetPropType<TypeTag, Properties::PrimaryVariables>;
    using NumEqVector = Dumux::NumEqVector<PrimaryVariables>;
    using GridView = typename GetPropType<TypeTag, Properties::GridGeometry>::GridView;
    using Element = typename GridView::template Codim<0>::Entity;

    using GridGeometry = GetPropType<TypeTag, Properties::GridGeometry>;
    using FVElementGeometry = typename GetPropType<TypeTag, Properties::GridGeometry>::LocalView;
    using SubControlVolumeFace = typename FVElementGeometry::SubControlVolumeFace;

    using GridVariables = GetPropType<TypeTag, Properties::GridVariables>;
    using ElementVolumeVariables = typename GridVariables::GridVolumeVariables::LocalView;
    using ElementFluxVariablesCache = typename GridVariables::GridFluxVariablesCache::LocalView;
    using TimeLoopPtr = std::shared_ptr<TimeLoop<Scalar>>;
    using FluidState = GetPropType<TypeTag, Properties::FluidState>;
    using SolutionVector = GetPropType<TypeTag, Properties::SolutionVector>;
    using Extrusion = Extrusion_t<GridGeometry>;
    using VolumeVariables = GetPropType<TypeTag, Properties::VolumeVariables>;
    enum
        {
            dimWorld = GridView::dimensionworld
        };
    // copy some indices for convenience
    using Indices = typename GetPropType<TypeTag, Properties::ModelTraits>::Indices;
    
    // primary variable indices
        enum
        {
            pressureIdx = Indices::pressureIdx,
        };

        // phase indices
        enum
        {
            gasPhaseIdx = FluidSystem::compIdx(FluidSystem::MultiPhaseFluidSystem::gasPhaseIdx),
            liquidPhaseIdx = FluidSystem::compIdx(FluidSystem::MultiPhaseFluidSystem::liquidPhaseIdx),
            H2OIdx = FluidSystem::compIdx(FluidSystem::MultiPhaseFluidSystem::H2OIdx),
            N2Idx = FluidSystem::compIdx(FluidSystem::MultiPhaseFluidSystem::N2Idx),
            CO2Idx = FluidSystem::compIdx(FluidSystem::MultiPhaseFluidSystem::CO2Idx),
            H2Idx = FluidSystem::compIdx(FluidSystem::MultiPhaseFluidSystem::H2Idx),
            CH4Idx = FluidSystem::compIdx(FluidSystem::MultiPhaseFluidSystem::CH4Idx),

        };
        // equation indices
        enum
        {
            numComponents = FluidSystem::compIdx(FluidSystem::MultiPhaseFluidSystem::numComponents),
            contiH2OEqIdx = Indices::conti0EqIdx + H2OIdx,
            contiN2EqIdx = Indices::conti0EqIdx + N2Idx,
            contiCO2EqIdx = Indices::conti0EqIdx + CO2Idx,
            contiH2EqIdx = Indices::conti0EqIdx + H2Idx,
            contiCH4EqIdx = Indices::conti0EqIdx + CH4Idx,
        };

    //! Property that defines whether mole or mass fractions are used
    static constexpr bool useMoles = getPropValue<TypeTag, Properties::UseMoles>();
    static const bool isBox = GetPropType<TypeTag, Properties::GridGeometry>::discMethod == DiscretizationMethods::box;

    using GlobalPosition = typename SubControlVolumeFace::GlobalPosition;
    using Dimension_vector = Dune::FieldVector<Scalar, dimWorld>;
public:
    OnePTwoCTestProblem(std::shared_ptr<const GridGeometry> gridGeometry)
    : ParentType(gridGeometry)
    {
        if (getParam<bool>("Problem.EnableGravity", true))
                gravity_ = {0, -9.81};
        //initialize fluid system
        FluidSystem::init();
        name_ = getParam<std::string>("Problem.Name");
        cells_ = getParam<Dimension_vector>("Grid.Cells");
        upperRight_ = getParam<Dimension_vector>("Grid.UpperRight");
        lowerLeft_ = getParam<Dimension_vector>("Grid.LowerLeft");
        // TODO: Generalize these domain helpers for  locally refined grids.
        xMax_ = upperRight_[0];
        xMin_ = lowerLeft_[0];
        yMax_ = upperRight_[1];
        yMin_ = lowerLeft_[1];
        deltaX_ = (xMax_ - xMin_);
        deltaX_ = deltaX_ / cells_[0];
        deltaY_ = (yMax_ - yMin_);
        deltaY_ = deltaY_ / cells_[1];
    }

    const std::string &name() const
    {
        return name_;
    }
    /*!
     * \name Problem parameters
     */
    // \{

    // \}

    /*!
     * \name Boundary conditions
     */
    // \{

    /*!
     * \brief Specifies which kind of boundary condition should be
     *        used for which equation on a given boundary segment.
     *
     * \param globalPos The position for which the bc type should be evaluated
     */
    BoundaryTypes boundaryTypesAtPos(const GlobalPosition &globalPos) const
    {
        BoundaryTypes values;
        // values.setAllNeumann();
        if(isRightBoundary_(globalPos))
            values.setAllDirichlet();
        else
        values.setAllNeumann();

        return values;
    }

    /*!
     * \brief Evaluates the boundary conditions for a Dirichlet boundary segment.
     *
     * \param globalPos The position for which the bc type should be evaluated
     */
    PrimaryVariables dirichletAtPos(const GlobalPosition &globalPos) const
    {
        PrimaryVariables values = initial_(globalPos);
        return values;
    }
     /*!
     * \brief Evaluates the boundary conditions for a neumann
     *        boundary segment (implementation for the tpfa scheme).
     */
     template<bool useBox = isBox, std::enable_if_t<!useBox, int> = 0>
     NumEqVector neumann(const Element& element,
                         const FVElementGeometry& fvGeometry,
                         const ElementVolumeVariables& elemVolVars,
                         const ElementFluxVariablesCache& elemFluxVarsCache,
                         const SubControlVolumeFace& scvf) const
    {
        // TPFA overload; the Box overload below is the main implementation used here.
        NumEqVector values(0.0);
        const auto& ipGlobal = scvf.ipGlobal();
        const auto &globalPos = scvf.ipGlobal();
        const auto& volVars = elemVolVars[scvf.insideScvIdx()];
        Scalar Time = this->time();
        NumEqVector injectionComposition_(0.0);

        // TODO: Extract the well schedule and injection composition into a shared helper
        // used by neumann() and postTimeStep() to avoid duplicated timing logic.
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

        // TODO: Move well-region definitions to input parameters so layouts do not require recompilation.
        if (isWellBoundary_(globalPos, inj_interval) && (Time < developmentDuration))
        {
            const int cycleNumber = std::floor(Time/(injectionDurationDev+idleDurationDev));
            const Scalar localTimeInCycle = Time - cycleNumber*(injectionDurationDev+idleDurationDev);
            if(localTimeInCycle <= injectionDurationDev){
                for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                {
                    values[compIdx] = injectionComposition_[compIdx] * inj_rate_dev ;
                }   
            }  
        }
        if (isWellBoundary_(globalPos, inj_interval) && (Time >= developmentDuration))
        {
            if(localTimeInCycle < injectionDurationOp){
                for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                {
                    values[compIdx] = injectionComposition_[compIdx] * inj_rate_Op;    
                }
            }
            if (localTimeInCycle > injectionDurationOp + idleDurationOp ){
                for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                {
                    Scalar X_GAS = volVars.moleFraction(gasPhaseIdx, compIdx);
                    values[compIdx] = (Extractionrate_)*X_GAS;
                }
            }

        }
        
        if (isRightBoundary_(globalPos))
        { 
            // Pressure outlet for the TPFA overload.
            auto init_val = initial_(globalPos);
            static const Scalar dirichletPressure = init_val[0];
            const auto& volVars = elemVolVars[scvf.insideScvIdx()];

            auto d = ipGlobal - element.geometry().center();
            d /= d.two_norm2();

            auto upwindTerm = useMoles ? volVars.molarDensity() : volVars.density();
            upwindTerm *= volVars.mobility();

            const auto tij = vtmv(scvf.unitOuterNormal(), volVars.permeability(), d);
            const auto phaseFlux = -1.0*upwindTerm*tij*(dirichletPressure - volVars.pressure());

            // set Neumann bc values
            // values[contiH2OEqIdx] = phaseFlux;
            // emulate an outflow condition for the component transport on the right side
            // values[contiN2EqIdx] = phaseFlux * (useMoles ? volVars.moleFraction(0, N2Idx) : volVars.massFraction(0, N2Idx));

            for (int compIdx = 0; compIdx < numComponents; ++compIdx)
            {
                values[compIdx] = ((phaseFlux * volVars.moleFraction(0, compIdx)));
            }
        }

        return values;
    }

    /*!
     * \brief Evaluates the boundary conditions for a neumann
     *        boundary segment (implementation for the box scheme).
     *
     * This is the method for the case where the Neumann condition is
     * potentially solution dependent and requires some quantities that
     * are specific to the fully-implicit method.
     *
     * \param element The finite element
     * \param fvGeometry The finite-volume geometry
     * \param elemVolVars All volume variables for the element
     * \param elemFluxVarsCache Flux variables caches for all faces in stencil
     * \param scvf The sub-control volume face
     *
     * For this method, the \a values parameter stores the flux
     * in normal direction of each phase. Negative values mean influx.
     * E.g. for the mass balance that would be the mass flux in \f$ [ kg / (m^2 \cdot s)] \f$.
     */
    template<bool useBox = isBox, std::enable_if_t<useBox, int> = 0>
    NumEqVector neumann(const Element &element,
                            const FVElementGeometry &fvGeometry,
                            const ElementVolumeVariables &elemVolVars,
                            const ElementFluxVariablesCache &elemFluxVarsCache,
                            const SubControlVolumeFace &scvf) const
    {   
        // TODO: Extract the well schedule and injection composition into a shared helper
        // used by neumann() and postTimeStep() to avoid duplicated timing logic.
        
        // Default is no-flow; the well interval and pressure outlet add boundary fluxes.
        NumEqVector values(0.0);
        // return values;

        const auto &globalPos = scvf.ipGlobal();
        const auto& volVars = elemVolVars[scvf.insideScvIdx()];
        Scalar Time = this->time();
        NumEqVector injectionComposition_(0.0);

        // Case schedule: development cycles inject cushion gas; operation cycles
        // alternate between H2 injection, idle time, and extraction.
        static const Scalar cylcesDev            = getParam<double>("BoundaryConditions.CyclesDev");
        static const Scalar injectionDurationDev = getParam<double>("BoundaryConditions.InjectionDurationDev")*86400;
        static const Scalar idleDurationDev     = getParam<double>("BoundaryConditions.IdleDurationDev")*86400;
        static const Scalar developmentDuration = cylcesDev*(injectionDurationDev+idleDurationDev);
        static const Scalar idleDurationOp     = getParam<double>("BoundaryConditions.IdleDurationOp")*86400;
        static const Scalar injectionDurationOp = getParam<double>("BoundaryConditions.InjectionDurationOp")*86400;
        static const Scalar extractionDurationOp = getParam<double>("BoundaryConditions.ExtractionDurationOp")*86400;
        double inj_rate_dev                     = getParam<double>("BoundaryConditions.InjectionRateDev");
        const int cycleNumberOp                 = std::floor((Time - developmentDuration)/(injectionDurationOp+extractionDurationOp + idleDurationOp));
        const Scalar localTimeInCycle           = Time - developmentDuration - cycleNumberOp*(injectionDurationOp + extractionDurationOp + idleDurationOp);
        double inj_rate_Op = getParam<double>("BoundaryConditions.InjectionRateOp", 0.0);
        double Extractionrate_ = getParam<double>("BoundaryConditions.ProductionRate", 0.0);
        double inj_interval = getParam<double>("BoundaryConditions.Well_Height", 0.0);
        auto CushionGasType_ = getParam<std::string>("BoundaryConditions.CushionGasType");
        // Development injection composition is selected from the input file.
        if (CushionGasType_ == "CH4")
            injectionComposition_[CH4Idx] = 1.0;
        else if (CushionGasType_ == "CO2")
            injectionComposition_[CO2Idx] = 1.0;
        else if (CushionGasType_ == "H2")
            injectionComposition_[H2Idx] = 1.0;
        else if (CushionGasType_ == "N2")
            injectionComposition_[N2Idx] = 1.0;
        else
        DUNE_THROW(Dune::InvalidStateException, "Invalid Cushion Gas Type " << CushionGasType_);

        // Development period: inject the selected cushion gas on the well boundary.
        if (isWellBoundary_(globalPos, inj_interval) && (Time < developmentDuration))
        {
            const int cycleNumber = std::floor(Time/(injectionDurationDev+idleDurationDev));
            const Scalar localTimeInCycle = Time - cycleNumber*(injectionDurationDev+idleDurationDev);
            if(localTimeInCycle <= injectionDurationDev){
                for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                {
                    values[compIdx] = injectionComposition_[compIdx] * inj_rate_dev ;
                }   
            }  
        }
        // Operation period: switch between H2 injection and extraction of the local gas mixture.
        if (isWellBoundary_(globalPos, inj_interval) && (Time >= developmentDuration))
        {
            if(localTimeInCycle < injectionDurationOp){
                values[H2Idx] = inj_rate_Op;  
            }
            if (localTimeInCycle > injectionDurationOp + idleDurationOp ){
                for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                {
                    Scalar X_GAS = volVars.moleFraction(gasPhaseIdx, compIdx);
                    values[compIdx] = (Extractionrate_)*X_GAS;
                }
            }

        }
        if (isRightBoundary_(globalPos))
        {               
            // Pressure outlet for the Box method: reconstruct the pressure gradient
            // from shape-function gradients, then distribute the phase flux by composition.
            Scalar dirichletPressure(0.0);
            auto init_val = initial_(globalPos);
            const auto &volVars = elemVolVars[scvf.insideScvIdx()];
            const auto &fluxVarsCache = elemFluxVarsCache[scvf];
            dirichletPressure = init_val[0];
            // evaluate the pressure gradient
            GlobalPosition gradP(0.0);
                for (const auto &scv : scvs(fvGeometry))
                {
                    const auto xIp = scv.dofPosition()[0];
                    auto tmp = fluxVarsCache.gradN(scv.localDofIndex());
                    tmp *= xIp > xMax_ - eps_ ? dirichletPressure
                                                : elemVolVars[scv].pressure();

                        gradP += tmp;


                }

            auto phaseFlux = vtmv(scvf.unitOuterNormal(), volVars.permeability(), gradP);
        
            phaseFlux *= -1*volVars.mobility();
            phaseFlux *= useMoles ? volVars.molarDensity() : volVars.density();

            for (int compIdx = 0; compIdx < numComponents; ++compIdx)
            {
                values[compIdx] = ((phaseFlux * volVars.moleFraction(0, compIdx)));
            }
        }

        return values;
    }

   
   void postTimeStep(const SolutionVector &curSol,
                          const SolutionVector &pastSol,
                          const GridVariables &gridVariables,
                          const Scalar,
                          std::shared_ptr<const GridGeometry> fvGridGeometry)
    {   
        // TODO: Separate material-balance/output diagnostics from the physical problem definition.
        // This hook runs after each accepted time step and reconstructs global
        // inventory, boundary exchange, and material-balance diagnostics.
        Scalar t, dt, volume(0.0);
        NumEqVector inventory(0.0), inventoryPastSol(0.0), materialBalanceError(0.0);
        NumEqVector relativeMaterialBalanceError(0.0);
        Scalar averageReservoirPressure(0.0);
        t = this->time();
        Scalar Time = t;
        dt = this->timeStepSize();
        NumEqVector values_inj(0.0), values_prod(0.0), values_inj_dt(0.0), values_prod_dt(0.0);
        
        for (const auto &element : elements(this->gridGeometry().gridView(), Dune::Partitions::interior))
        {
            auto fvGeometry = localView(*fvGridGeometry);
            fvGeometry.bind(element);

            auto elemVolVars = localView(gridVariables.curGridVolVars());
            elemVolVars.bindElement(element, fvGeometry, curSol);
            auto prevElemVolVars = localView(gridVariables.prevGridVolVars());
            prevElemVolVars.bindElement(element, fvGeometry, pastSol);

            const auto elemSol = elementSolution(element, curSol, this->gridGeometry());
            const auto elemSolPast = elementSolution(element, pastSol, this->gridGeometry());
            auto elemFluxVarsCache = localView(gridVariables.gridFluxVarsCache());
            elemVolVars.bind(element, fvGeometry, curSol);
            elemFluxVarsCache.bind(element, fvGeometry, elemVolVars);

            // Integrate current and previous component inventories over all control volumes.
            for (auto &&scv : scvs(fvGeometry))
            {
                const FluidState &fs = elemVolVars[scv].fluidState();
                const FluidState &fsOld = prevElemVolVars[scv].fluidState();
                Scalar extrusion_ = Extrusion::volume(fvGeometry, scv);
                VolumeVariables volVars, volVarsPast;
                volVars.update(elemSol, *this, element, scv);
                volVarsPast.update(elemSolPast, *this, element, scv);
                for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                {
                    inventory[compIdx] += volVars.porosity() * extrusion_  * ((fs.saturation(gasPhaseIdx) * fs.molarDensity(gasPhaseIdx) * fs.moleFraction(gasPhaseIdx, compIdx) + fs.saturation(liquidPhaseIdx) * fs.molarDensity(liquidPhaseIdx) * fs.moleFraction(liquidPhaseIdx, compIdx)));
                    inventoryPastSol[compIdx] += volVarsPast.porosity() * extrusion_  * ((fsOld.saturation(gasPhaseIdx) * fsOld.molarDensity(gasPhaseIdx) * fsOld.moleFraction(gasPhaseIdx, compIdx) + fsOld.saturation(liquidPhaseIdx) * fsOld.molarDensity(liquidPhaseIdx) * fsOld.moleFraction(liquidPhaseIdx, compIdx)));
                }
                averageReservoirPressure += fs.pressure(gasPhaseIdx) * scv.volume();
                volume += scv.volume();
            }

            // Reconstruct well-boundary injection and production totals using the same
            // schedule as the Neumann boundary condition.
            NumEqVector injectionComposition_(0.0);
            static const Scalar cylcesDev            = getParam<double>("BoundaryConditions.CyclesDev");
            static const Scalar injectionDurationDev = getParam<double>("BoundaryConditions.InjectionDurationDev")*86400;
            static const Scalar idleDurationDev     = getParam<double>("BoundaryConditions.IdleDurationDev")*86400;
            static const Scalar developmentDuration = cylcesDev*(injectionDurationDev+idleDurationDev);
            static const Scalar idleDurationOp     = getParam<double>("BoundaryConditions.IdleDurationOp")*86400;
            static const Scalar injectionDurationOp = getParam<double>("BoundaryConditions.InjectionDurationOp")*86400;
            static const Scalar extractionDurationOp = getParam<double>("BoundaryConditions.ExtractionDurationOp")*86400;
            double inj_rate_dev                     = getParam<double>("BoundaryConditions.InjectionRateDev");
            const int cycleNumberOp                 = std::floor((Time - developmentDuration)/(injectionDurationOp+extractionDurationOp + idleDurationOp));
            const Scalar localTimeInCycle           = Time - developmentDuration - cycleNumberOp*(injectionDurationOp + extractionDurationOp + idleDurationOp);
            double inj_rate_Op = getParam<double>("BoundaryConditions.InjectionRateOp", 0.0);
            double Extractionrate_ = getParam<double>("BoundaryConditions.ProductionRate", 0.0);
            double inj_interval = getParam<double>("BoundaryConditions.Well_Height", 0.0);
            auto CushionGasType_ = getParam<std::string>("BoundaryConditions.CushionGasType");
            if (CushionGasType_ == "CH4")
                injectionComposition_[CH4Idx] = 1.0;
            else if (CushionGasType_ == "CO2")
                injectionComposition_[CO2Idx] = 1.0;
            else if (CushionGasType_ == "H2")
                injectionComposition_[H2Idx] = 1.0;
            else if (CushionGasType_ == "N2")
                injectionComposition_[N2Idx] = 1.0;
            else
            DUNE_THROW(Dune::InvalidStateException, "Invalid Cushion Gas Type " << CushionGasType_);

            // Loop over boundary faces and accumulate exchange rates over the well interval.
            for (auto&& scvf : scvfs(fvGeometry) )
            {   
                const auto& scv = fvGeometry.scv(scvf.insideScvIdx());
                VolumeVariables volVars, volVarsPast;
                volVars.update(elemSol, *this, element, scv);
                volVarsPast.update(elemSolPast, *this, element, scv);
                Scalar extrusion_  = Extrusion::area(fvGeometry, scvf);
                if (isWellBoundaryFace_(scvf, inj_interval))
                {
                    if (Time < developmentDuration)
                    {
                        const int cycleNumber = std::floor(Time/(injectionDurationDev+idleDurationDev));
                        const Scalar localTimeInCycle = Time - cycleNumber*(injectionDurationDev+idleDurationDev);
                        if(localTimeInCycle <= injectionDurationDev){
                            for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                            {
                                
                                values_inj[compIdx] += injectionComposition_[compIdx] * extrusion_ * inj_rate_dev;
                            }
                        }
                    }
                    if (Time >= developmentDuration)
                    {
                        if(localTimeInCycle < injectionDurationOp){

                            values_inj[H2Idx] +=  extrusion_ * inj_rate_Op;  

                        }
                        if (localTimeInCycle > injectionDurationOp + idleDurationOp ){
                            for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                            {
                                Scalar X_GAS = volVars.moleFraction(gasPhaseIdx, compIdx);
                                values_prod[compIdx] +=  extrusion_ *(Extractionrate_)*X_GAS;
                            }
                        }
                    }

                
                }
            }
        }
        const auto &comm = this->gridGeometry().gridView().comm();
            // Component-wise material-balance check:
            // previous inventory - current inventory - injected amount + produced amount.
            materialBalanceError = inventoryPastSol - inventory - dt * values_inj + dt * values_prod;

            for (int compIdx = 0; compIdx < numComponents; ++compIdx)
             {
                values_inj_dt[compIdx] = values_inj[compIdx] * dt;
                values_prod_dt[compIdx] = values_prod[compIdx] * dt;
            }

            for (int compIdx = 0; compIdx < numComponents; ++compIdx)
            {
                const Scalar globalError = comm.sum(materialBalanceError[compIdx]);
                const Scalar balanceScale = std::max(std::abs(comm.sum(inventoryPastSol[compIdx]))
                                                     + std::abs(comm.sum(values_inj_dt[compIdx]))
                                                     + std::abs(comm.sum(values_prod_dt[compIdx])),
                                                     eps_);
                relativeMaterialBalanceError[compIdx] = std::abs(globalError) / balanceScale;
            }

            if (comm.rank() == 0)
            {
                std::cout << "Relative material-balance error at t = " << t << " s:";
                for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                    std::cout << " " << FluidSystem::componentName(compIdx)
                              << "=" << relativeMaterialBalanceError[compIdx];
                std::cout << std::endl;
            }

            // Append parallel-reduced diagnostics to the JSON output file.
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
                collector["InjectionValues_dt"][FluidSystem::componentName(compIdx)].push_back(comm.sum(values_inj_dt[compIdx]));
                collector["ProductionValues_dt"][FluidSystem::componentName(compIdx)].push_back(comm.sum(values_prod_dt[compIdx]));
            }
            
            Dumux::MetaData::writeJsonFile(collector, name());
    }

    /*!
     * \name Volume terms
     */
    // \{

    /*!
     * \brief Evaluates the source term for all phases within a given
     *        sub-control volume.
     *
     * For this method, the \a priVars parameter stores the rate mass
     * of a component is generated or annihilated per volume
     * unit. Positive values mean that mass is created, negative ones
     * mean that it vanishes.
     *
     * The units must be according to either using mole or mass fractions (mole/(m^3*s) or kg/(m^3*s)).
     */
    NumEqVector sourceAtPos(const GlobalPosition &globalPos) const
    { return NumEqVector(0.0); }

    /*!
     * \brief Evaluates the initial value for a control volume.
     *
     * \param globalPos The position for which the initial condition should be evaluated
     *
     * For this method, the \a values parameter stores primary
     * variables.
     */
    PrimaryVariables initialAtPos(const GlobalPosition &globalPos) const
    { return initial_(globalPos); }

    // \}
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
    bool isRightBoundary_(const GlobalPosition& globalPos) const
    {
        return globalPos[0] > xMax_ - eps_;
    }

    bool isLeftBoundary_(const GlobalPosition& globalPos) const
    {
        return globalPos[0] < xMin_ + eps_;
    }

    bool isWithinWellInterval_(const GlobalPosition& globalPos, Scalar wellHeight) const
    {
        return globalPos[1] - yMin_ >= yMax_ - wellHeight;
    }

    bool isWellBoundary_(const GlobalPosition& globalPos, Scalar wellHeight) const
    {
        return isLeftBoundary_(globalPos) && isWithinWellInterval_(globalPos, wellHeight);
    }

    bool isWellBoundaryFace_(const SubControlVolumeFace& scvf, Scalar wellHeight) const
    {
        return scvf.boundary()
               && scvf.area() == deltaY_/2
               && scvf.center()[0] == xMin_
               && isWithinWellInterval_(scvf.center(), wellHeight);
    }

    // the internal method for the initial condition
    PrimaryVariables initial_(const GlobalPosition &globalPos) const
    {
        PrimaryVariables priVars;
        Scalar pressure_TOP = getParam<Scalar>("BoundaryConditions.Pressure_TOP", 100e5);
        FluidState fs;
        fs.setMoleFraction(gasPhaseIdx, CO2Idx, 0.0); fs.setMoleFraction(gasPhaseIdx, CH4Idx, 1.0);
        fs.setPressure(gasPhaseIdx, pressure_TOP);
        // fs.density(liquidPhaseIdx); fs.density(gasPhaseIdx);
        fs.setTemperature(this->spatialParams().temperatureAtPos(globalPos));     

        // Scalar pw = 0.0;
        // Scalar check = 1.0;
        // Scalar z = globalPos[dimWorld - 1];
        Scalar densityG = FluidSystem::density(fs, gasPhaseIdx);
        // priVars[pressureIdx] = 75e5; // initial condition for the pressure
        // priVars[contiCH4EqIdx] = 1.0;  // initial condition for the N2 molefraction
        priVars[pressureIdx]  = (pressure_TOP - (densityG * gravity()[dimWorld - 1] * (yMax_ - (globalPos)[dimWorld - 1])));
        return priVars;
    }
        TimeLoopPtr timeLoop_;
        static constexpr Scalar eps_ = 1e-6;
        Dimension_vector cells_;
        Dimension_vector upperRight_, lowerLeft_;
        double deltaX_ = 0.0;
        double deltaY_ = 0.0;
        double xMax_ = 0.0;
        double xMin_ = 0;
        double yMax_ = 0.0;
        double yMin_ = 0.0;
        std::string name_;
    };

} // end namespace Dumux

#endif
