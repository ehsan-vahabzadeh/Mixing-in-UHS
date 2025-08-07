// $Id: waterairproblem.hh 4185 2010-08-26 15:49:58Z lauser $
/*****************************************************************************
 *   Copyright (C) 2009 by Klaus Mosthaf                                     *
 *   Copyright (C) 2009 by Andreas Lauser                                    *
 *   Institute of Hydraulic Engineering                                      *
 *   University of Stuttgart, Germany                                        *
 *   email: <givenname>.<name>@iws.uni-stuttgart.de                          *
 *                                                                           *
 *   This program is free software: you can redistribute it and/or modify    *
 *   it under the terms of the GNU General Public License as published by    *
 *   the Free Software Foundation, either version 2 of the License. or       *
 *   (at your option) any later version.                                     *
 *                                                                           *
 *   This program is distributed in the hope that it will be useful,         *
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of          *
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           *
 *   GNU General Public License for more details.                            *
 *                                                                           *
 *   You should have received a copy of the GNU General Public License       *
 *   along with this program.  If not, see <http://www.gnu.org/licenses/>.   *
 *****************************************************************************/
#ifndef DUMUX_HPCOREPROBLEM_HH
#define DUMUX_HPCOREPROBLEM_HH

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

//#include <dune/grid/io/file/dgfparser/dgfug.hh>
//#include <dune/grid/io/file/dgfparser/dgfs.hh>
//#include <dune/grid/io/file/dgfparser/dgfyasp.hh>
//#include <dune/grid/io/file/dgfparser/dgfalu.hh>
#include <dune/grid/uggrid.hh>
#include <dumux/material/fluidsystems/biofluidsystem.hh>
#include <dumux/implicit/common/implicitporousmediaproblem.hh>
#include <dumux/implicit/2pncmin/2pncminmodel.hh>
#include <dumux/implicit/2pbiomin/2pbiominmodel.hh>
#include <dumux/implicit/2pbiomin/2pbiominfluxvariables.hh>
#include <dumux/implicit/2pbiomin/2pbiominlocalresidual.hh>
#include <dumux/implicit/2pbiomin/2pbiominvolumevariables.hh>
#include <dumux/implicit/2pncmin/2pncminvolumevariables.hh>

#include <dumux/material/binarycoefficients/brine_co2_varSal.hh>
#include <dumux/material/chemistry/biogeochemistry/biocarbonicacid.hh>

#include "hpcorespatialparams.hh"
#include "bioco2tables.hh"

#include "dumux/linear/seqsolverbackend.hh"


#define ISOTHERMAL 1

/*!
 * \ingroup BoxProblems
 * \brief TwoPNCMinBoxProblems  two-phase n-component mineralisation box problems
 */

namespace Dumux
{
template <class TypeTag>
class BioMinProblem;

namespace Properties
{
NEW_TYPE_TAG(BioMinProblem, INHERITS_FROM(BoxTwoPNCMin, BioMinSpatialParams));
//NEW_TYPE_TAG(BioMinProblem, INHERITS_FROM(BoxTwoBioMin, BioMinSpatialParams));

// Set the grid type
SET_PROP(BioMinProblem, Grid)
{
    typedef Dune::UGGrid<2> type;
//   typedef Dune::YaspGrid<2> type;
};

// Set the problem property
SET_PROP(BioMinProblem, Problem)
{
    typedef Dumux::BioMinProblem<TTAG(BioMinProblem)> type;
};

SET_PROP(BioMinProblem, FluidSystem)
{
    typedef typename GET_PROP_TYPE(TypeTag, Scalar) Scalar;
    typedef Dumux::BioMin::CO2Tables CO2Tables;
    typedef Dumux::TabulatedComponent<Scalar, Dumux::H2O<Scalar>> H2O_Tabulated;
    static const bool useComplexRelations = true;
    typedef Dumux::FluidSystems::BioFluid<TypeTag, Scalar, CO2Tables, H2O_Tabulated, useComplexRelations> type;
};

//! the BioMin Flux VolumeVariables and LocalResidual properties

SET_TYPE_PROP(BioMinProblem, FluxVariables, TwoPBioMinFluxVariables<TypeTag>);
SET_TYPE_PROP(BioMinProblem, VolumeVariables, TwoPBioMinVolumeVariables<TypeTag>);
SET_TYPE_PROP(BioMinProblem, LocalResidual, TwoPBioMinLocalResidual<TypeTag>);
SET_TYPE_PROP(BioMinProblem, Model, TwoPBioMinModel<TypeTag>);

//SET_TYPE_PROP(BioMinProblem, LinearSolver, SuperLUBackend<TypeTag>);

SET_PROP(BioMinProblem, Chemistry)
{
    typedef Dumux::BioMin::CO2Tables CO2Tables;
    typedef Dumux::BioCarbonicAcid<TypeTag, CO2Tables> type;
};

// Set the spatial parameters
SET_TYPE_PROP(BioMinProblem,
              SpatialParams,
              Dumux::BioMinSpatialParams<TypeTag>);





}

/*!
 * \ingroup TwoPTwoCNIBoxProblems
 * \brief Measurement of Brine displacement due to CO2 injection
 *  */
template <class TypeTag = TTAG(BioMinProblem) >
class BioMinProblem : public ImplicitPorousMediaProblem<TypeTag>
{
    typedef typename GET_PROP_TYPE(TypeTag, Scalar) Scalar;
    typedef typename GET_PROP_TYPE(TypeTag, GridView) GridView;
    typedef typename GET_PROP_TYPE(TypeTag, Model) Model;
    typedef typename GridView::Grid Grid;

    typedef typename GET_PROP_TYPE(TypeTag, Chemistry) Chemistry;

    typedef BioMinProblem<TypeTag> ThisType;
    typedef ImplicitPorousMediaProblem<TypeTag> ParentType;

    // copy some indices for convenience
    typedef typename GET_PROP_TYPE(TypeTag, Indices) Indices;
    typedef typename GET_PROP_TYPE(TypeTag, FluidSystem) FluidSystem;

    enum {
        numEq = GET_PROP_VALUE(TypeTag, NumEq),
        numComponents = FluidSystem::numComponents,
        numSecComponents = FluidSystem::numSecComponents,
        numSPhases = FluidSystem::numSPhases,

        pressureIdx = Indices::pressureIdx,
        switchIdx = Indices::switchIdx, //Saturation
        xlNaIdx = FluidSystem::NaIdx,
        xlClIdx = FluidSystem::ClIdx,
        xlCaIdx = FluidSystem::CaIdx,
        xlUreaIdx = FluidSystem::UreaIdx,
        xlTNHIdx = FluidSystem::TNHIdx,
        xlO2Idx = FluidSystem::O2Idx,
        xlBiosubIdx = FluidSystem::BiosubIdx,
        xlBiosuspIdx = FluidSystem::BiosuspIdx,
        phiBiofilmIdx = numComponents,//FluidSystem::BiofilmIdx,
        phiCalciteIdx = numComponents + 1,//FluidSystem::CalciteIdx,

#if !ISOTHERMAL
        temperatureIdx = Indices::temperatureIdx,
        energyEqIdx = Indices::energyEqIdx,
#endif

        //Indices of the components
        wCompIdx = FluidSystem::wCompIdx,
        nCompIdx = FluidSystem::nCompIdx,
        NaIdx = FluidSystem::NaIdx,
        ClIdx = FluidSystem::ClIdx,
        CaIdx = FluidSystem::CaIdx,
        UreaIdx = FluidSystem::UreaIdx,
        TNHIdx = FluidSystem::TNHIdx,
        O2Idx = FluidSystem::O2Idx,
        BiosubIdx = FluidSystem::BiosubIdx,
        BiosuspIdx = FluidSystem::BiosuspIdx,

        NH4Idx = FluidSystem::NH4Idx,
        CO3Idx = FluidSystem::CO3Idx,
        HCO3Idx = FluidSystem::HCO3Idx,
        CO2Idx = FluidSystem::CO2Idx,
        HIdx = FluidSystem::HIdx,
        OHIdx = FluidSystem::OHIdx,

        BiofilmIdx = FluidSystem::BiofilmIdx,
        CalciteIdx = FluidSystem::CalciteIdx,

        wPhaseIdx = FluidSystem::wPhaseIdx,
        nPhaseIdx = FluidSystem::nPhaseIdx,
        bPhaseIdx = FluidSystem::bPhaseIdx,
        cPhaseIdx = FluidSystem::cPhaseIdx,

        //Index of the primary component of G and L phase
        conti0EqIdx = Indices::conti0EqIdx,

        // Phase State
        wPhaseOnly = Indices::wPhaseOnly,
        nPhaseOnly = Indices::nPhaseOnly,
        bothPhases = Indices::bothPhases,

        // Grid and world dimension
        dim = GridView::dimension,
        dimWorld = GridView::dimensionworld,
    };


    typedef typename GET_PROP_TYPE(TypeTag, PrimaryVariables) PrimaryVariables;
    typedef typename GET_PROP_TYPE(TypeTag, BoundaryTypes) BoundaryTypes;
    typedef typename GET_PROP_TYPE(TypeTag, TimeManager) TimeManager;
    typedef typename GET_PROP_TYPE(TypeTag, ElementVolumeVariables) ElementVolumeVariables;
    typedef typename GET_PROP_TYPE(TypeTag, VolumeVariables) VolumeVariables;

    typedef typename GridView::template Codim<0>::Entity Element;
    typedef typename GridView::template Codim<dim>::Entity Vertex;
    typedef typename GridView::Intersection Intersection;
   // typedef Dune::FieldVector<Scalar, numComponents> ComponentVector;
    typedef typename GET_PROP_TYPE(TypeTag, FVElementGeometry) FVElementGeometry;
    typedef Dune::FieldVector<Scalar, dim> LocalPosition;
    typedef Dune::FieldVector<Scalar, dimWorld> GlobalPosition;

    typedef Dumux::BinaryCoeff::Brine_CO2<Scalar, Dumux::BioMin::CO2Tables, true> Brine_CO2;

//    typedef Dune::FieldVector<Scalar, numComponents + numSecComponents> CompVector;

public:
    BioMinProblem(TimeManager &timeManager, const GridView &gridView)
        : ParentType(timeManager, gridView)
    {

        try
    {
            name_  = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, std::string, Problem, Name);

            dtmax_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, TimeManager, DtMax);

            //initial values
            densityW_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Initial, initDensityW);
            initPressure_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Initial, initPressure);

            initxlTC_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Initial, initxlTC);
            initxlNa_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Initial, initxlNa);
            initxlCl_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Initial, initxlCl);
            initxlCa_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Initial, initxlCa);
            initxlUrea_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Initial, initxlUrea);
            initxlTNH_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Initial, initxlTNH);
            initxlO2_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Initial, initxlO2);
            initxlBiosub_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Initial, initxlSubstrate);
            initxlBiosusp_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Initial, initxlBiosusp);

            initBiofilm_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Initial, initBiofilm);
            initCalcite_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Initial, initCalcite);

            initPorosity_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, SpatialParams, Porosity);

            xlNaCorr_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Initial, xlNaCorr);
            xlClCorr_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Initial, xlClCorr);

            //injection values
            injTC_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Injection, injTC);
            injNa_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Injection, injNa);
//          injCl_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Injection, injCl);
            injCa_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Injection, injCa);
            injUrea_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Injection, injUrea);
            injTNH_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Injection, injTNH);
            injO2_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Injection, injO2);
            injSub_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Injection, injSub);
            injBiosusp_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Injection, injBiosusp);

            injNaCorr_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Injection, injNaCorr);

            numInjections_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Injection, numInjections);
            injectionParameters_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, std::string, Injection, InjectionParamFile);
    }

    catch (Dumux::ParameterException &e) {
        std::cerr << e << ". Abort!\n";
        exit(1) ;
    }

        std::ifstream injectionData;
        std::string row;
        injectionData.open( injectionParameters_); // open the Injection data file
        if (not injectionData.is_open())
        {
             std::cerr << "\n\t -> Could not open file '"
                      << injectionParameters_
                      << "'. <- \n\n\n\n";
            exit(1) ;
        }
        Scalar tempTime = 0;
        int tempType = 0;
        Scalar tempQ = 0;

        // print file to make sure it is the right file
        std::cout << "Read file: " << "injectionParameters_" << " ..." << std::endl << std::endl;
        while(!injectionData.eof())
        {
            getline(injectionData, row);
            std::cout << row << std::endl;
        }
        injectionData.close();

        //read data from file
        injectionData.open(injectionParameters_);

        while(!injectionData.eof())
        {
            getline(injectionData, row);

            if(row == "EndTimes")
                {
                getline(injectionData, row);
                while(row != "#")
                    {
                    if (row != "#")
                        {
                        std::istringstream ist(row);
                        ist >> tempTime;
                        epiEnd_.push_back(tempTime);
                        }
                    getline(injectionData, row);
                    }
                std::cout << "size of EpiEnd: "<<epiEnd_.size() << std::endl;
                }
            if(row == "InjectionTypes")
                {
                getline(injectionData, row);
                while(row != "#")
                    {
                    if (row != "#")
                        {
                        std::istringstream ist(row);
                        ist >> tempType;
                        injType_.push_back(tempType);
                        }
                    getline(injectionData, row);
                    }
                std::cout << "size of injType: "<<injType_.size() << std::endl;
                }
            if(row == "InjectionQ")
                {
                getline(injectionData, row);
                while(row != "#")
                    {
                    if (row != "#")
                        {
                        std::istringstream ist(row);
                        ist >> tempQ;
                        tempQ /= 60;
                        tempQ /= 1e6;  //TODO injectionQ in the parameter file is specified in ml/min ! convert to m³/s
                        injQ_.push_back(tempQ);
                        }
                    getline(injectionData, row);
                    }
                std::cout << "injQ [m³/s]: "<< std::endl;
                for( int i=0; i<injQ_.size(); ++i)
                    std::cout << injQ_[i] << std::endl;
                std::cout << "size of injQ: "<<injQ_.size() << std::endl;
                }
        }

        injectionData.close();

//      check the injection data against the number of injections specified in the parameter file
        if (epiEnd_.size() != numInjections_)
        {
            std::cerr <<  "numInjections from the parameterfile and the number of injection end times specified in the injection data file do not match!"
                    <<"\n numInjections from parameter file = "<<numInjections_
                    <<"\n numEpisodes from injection data file = "<<epiEnd_.size()
                    <<"\n Abort!\n";
            exit(1) ;
        }
        if (injType_.size() != numInjections_)
        {
            std::cerr <<  "numInjections from the parameterfile and the number of injection types specified in the injection data file do not match!"
                    <<"\n numInjections from parameter file = "<<numInjections_
                    <<"\n numInjTypes from injection data file = "<<injType_.size()
                    <<"\n Abort!\n";
            exit(1) ;
        }       if (injQ_.size() != numInjections_)
        {
            std::cerr <<  "numInjections from the parameterfile and the number of injection volume fluxes specified in the injection data file do not match!"
                    <<"\n numInjections from parameter file = "<<numInjections_
                    <<"\n numInjQ from injection data file = "<<injQ_.size()
                    <<"\n Abort!\n";
            exit(1) ;
        }

        FluidSystem::init();
        this->timeManager().startNextEpisode(EpisodeEnd(0));
        this->newtonController().setMaxSteps(15);
    }

    bool shouldWriteOutput() const
        {
            return
//                  this->timeManager().timeStepIndex() % 1 == 0 ||         //output every timestep
                    this->timeManager().timeStepIndex() % 1000 == 0 ||          //output every 1000 timesteps
                this->timeManager().timeStepIndex() == 0 ||
                this->timeManager().episodeWillBeOver() ||
                this->timeManager().willBeFinished();
        }

    bool shouldWriteRestartFile() const
    {
        return
//                  this->timeManager().timeStepIndex() % 1 == 0 ||         // every timestep
//              this->timeManager().timeStepIndex() % 1000 == 0 ||          // every 1000 timesteps
            this->timeManager().episodeWillBeOver();
    }

    void preTimeStep()
    {
        if (this->timeManager().timeStepSize()>dtmax_) //hier willkürlich, Anozie hat für die Säulenexperimente auf Tepisodemin/2 begrenzt!
        {
            this->timeManager().setTimeStepSize(dtmax_);
        }
    }

    /*!
     * \name Problem parameters
     */


    /*!
     * \brief The problem name.
     *
     * This is used as a prefix for files generated by the simulation.
     */
    //const char *name() const
    const std::string name() const
    { //return "HP-Core1";
        return name_;
    }

#if ISOTHERMAL
    /*!
     * \brief Returns the temperature within the domain.
     *
     * This problem assumes a temperature of 10 degrees Celsius.
     */
    Scalar temperature(const Element &element,
                       const FVElementGeometry &fvGeometry,
                       int scvIdx) const
    {
        return 273.15 + 25; // -> 25 deg C
    };
#endif

    // \}

    /*!
     * \name Boundary conditions
     */
    // \{

    /*!
     * \brief Specifies which kind of boundary condition should be
     *        used for which equation on a given boundary segment.
     */
    void boundaryTypes(BoundaryTypes &values, const Vertex &vertex) const
    {
        const GlobalPosition globalPos = vertex.geometry().center();
        Scalar xmax = this->bBoxMax()[0];
        values.setAllNeumann();
        if(globalPos[0] > xmax - eps_)
            {
            values.setDirichlet(pressureIdx);
            for (int i=switchIdx; i< numEq - numSPhases; ++i)
            {
//              values.setOutflow(i);
                values.setDirichlet(i);
            }
        }
    }

    /*!
     * \brief Evaluate the boundary conditions for a dirichlet
     *        boundary segment.
     *
     * For this method, the \a values parameter stores primary variables.
     */
    void dirichlet(PrimaryVariables &values, const Vertex &vertex) const
    {
        const GlobalPosition globalPos = vertex.geometry().center();

            initial_(values,globalPos);
            values[xlBiosubIdx] = 0.0;
            values[xlO2Idx] = 0.0;
    }

    /*!
     * \brief Evaluate the boundary conditions for a neumann
     *        boundary segment.
     *
     * For this method, the \a values parameter stores the mass flux
     * in normal direction of each component. Negative values mean
     * influx.
     */
    void neumann(PrimaryVariables &values,
                      const Element &element,
                      const FVElementGeometry &fvGeometry,
                      const Intersection &is,
                      int scvIdx,
                      int boundaryFaceIdx) const

    {
        const GlobalPosition &globalPos =fvGeometry.boundaryFace[boundaryFaceIdx].ipGlobal;

        int episodeIdx = this->timeManager().episodeIndex()-1;
        Scalar diameter = this->bBoxMax()[1];
        Scalar waterflux = injQ_[episodeIdx]/(3.14*diameter*diameter/4.); //[m/s]               //TODO assumes round core and correct width of the grid

        int InjProcess = -99; //no flow as default
        if (episodeIdx < injType_.size())
            InjProcess = injType_[episodeIdx];

//         negative values for injection
        if(globalPos[0]<= eps_)
        {
        //basic rinse injection (InjProcess == -1 )
        values[conti0EqIdx + wCompIdx] = -waterflux * 996/FluidSystem::molarMass(wCompIdx);
        values[conti0EqIdx + nCompIdx] = -waterflux * injTC_*996 /FluidSystem::molarMass(nCompIdx);
        values[conti0EqIdx + xlCaIdx] = 0;
        values[conti0EqIdx + xlBiosuspIdx] = 0;
        values[conti0EqIdx + xlBiosubIdx] = -waterflux * injSub_ /FluidSystem::molarMass(xlBiosubIdx);
        values[conti0EqIdx + xlO2Idx] = -waterflux * injO2_ /FluidSystem::molarMass(O2Idx);
        values[conti0EqIdx + xlUreaIdx] = 0;
        values[conti0EqIdx + xlTNHIdx] = -waterflux * injTNH_ /FluidSystem::molarMass(TNHIdx);
        values[conti0EqIdx + phiCalciteIdx] = 0;
        values[conti0EqIdx + phiBiofilmIdx] = 0;
        values[conti0EqIdx + xlNaIdx] = -waterflux * (injNa_ + injNaCorr_) /FluidSystem::molarMass(NaIdx);
        values[conti0EqIdx + xlClIdx] = -waterflux *injTNH_ /FluidSystem::molarMass(TNHIdx)     //NH4Cl --->  mol Cl = mol NH4
                                        -waterflux *injNa_ /FluidSystem::molarMass(NaIdx);      //NaCl ---> mol Cl = mol Na

        if (InjProcess == -1)   // rinse, used as standard injection fluid
        {
            //          do not change anything.
        }

        else if (InjProcess == -99) // no injection
        {
            values = 0.0; //mol/m²/s
        }

        else if (InjProcess == 1)       //ca-rich injection: ca and urea injected additionally to rinse-fluid, Na (pH) and Cl are also different(CaCl2)
        {
            values[conti0EqIdx + wCompIdx] = - waterflux * 0.8716 * densityW_ /FluidSystem::molarMass(wCompIdx);    //TODO 0.8716 check factor!!!
            values[conti0EqIdx + nCompIdx] = - waterflux * injTC_ * densityW_ /FluidSystem::molarMass(nCompIdx);
            values[conti0EqIdx + xlCaIdx] = - waterflux * injCa_/FluidSystem::molarMass(CaIdx);
            values[conti0EqIdx + xlUreaIdx] = - waterflux * injUrea_ /FluidSystem::molarMass(UreaIdx);
            values[conti0EqIdx + xlNaIdx] = - waterflux * injNa_ /FluidSystem::molarMass(NaIdx)
                                            - waterflux * injNaCorr_ /FluidSystem::molarMass(NaIdx)* 0.032;
            values[conti0EqIdx + xlClIdx] = - waterflux * injTNH_ /FluidSystem::molarMass(TNHIdx)               //NH4Cl --->  mol Cl = mol NH4
                                            - waterflux * 2 * injCa_/FluidSystem::molarMass(CaIdx)              //+CaCl2 --->  mol Cl = mol Ca*2
                                            - waterflux *injNa_ /FluidSystem::molarMass(NaIdx);         //NaCl ---> mol Cl = mol Na
        }

        else if (InjProcess == 0 || InjProcess == 3 )   //urea-injections: urea is injected additionally to rinse-fluid
        {
            values[conti0EqIdx + xlUreaIdx] = - waterflux * injUrea_ /FluidSystem::molarMass(UreaIdx);
        }

        else if(InjProcess == 2)        //inoculation: same as rinse, but with bacteria
        {
            values[conti0EqIdx + xlBiosuspIdx] = -waterflux * injBiosusp_ /FluidSystem::molarMass(xlBiosuspIdx);
        }
            else
            {
                DUNE_THROW(Dune::InvalidStateException, "Invalid injection process " << InjProcess);
            }
        }
        else
        {
            values = 0.0; //mol/m²/s
        }
  }

    /*!
     * \brief Evaluate the source term for all phases within a given
     *        sub-control-volume.
     *
     * For this method, the \a values parameter stores the rate mass
     * of a component is generated or annihilate per volume
     * unit. Positive values mean that mass is created, negative ones
     * mean that it vanishes.
     */
    void source(PrimaryVariables &q,
              const Element &element,
              const FVElementGeometry &fvGeometry,
                int scvIdx) const
    {
        q = 0;
    }

    /*!
     * \brief Evaluate the source term for all phases within a given
     *        sub-control-volume due to chemical reactions.
     *
     * For this method, the \a values parameter stores the rate mass
     * of a component is generated or annihilate per volume
     * unit. Positive values mean that mass is created, negative ones
     * mean that it vanishes.
     */
    void reactionSource(PrimaryVariables &q,
                const Element &element,
                const FVElementGeometry &fvGeometry,
                int scvIdx,
                const VolumeVariables &volVars,
                const Scalar absgradpw) const
    {

        q = 0;

        Scalar dt = this->timeManager().timeStepSize();

        Chemistry chemistry;
        chemistry.reactionSource(q,
                        volVars,
                        absgradpw,
                        dt);
    }

    /*!
     * \brief Evaluate the initial value for a control volume.
     *
     * For this method, the \a values parameter stores primary
     * variables.
     */
    void initial(PrimaryVariables &values,
                 const Element &element,
                 const FVElementGeometry &fvGeometry,
                 int scvIdx) const
    {
        const GlobalPosition &globalPos = element.geometry().corner(scvIdx);
        initial_(values, globalPos);
    }

    /*!
     * \brief Return the initial phase state inside a control volume.
     */
    int initialPhasePresence(const Vertex &vert,
                             int &globalIdx,
                             const GlobalPosition &globalPos) const
    {
        return wPhaseOnly;
//      return bothPhases;
    }

    Scalar refValue(int EqIdx)
    {
//      Scalar refValue = refValue_[EqIdx];
        Scalar refValue = 0;
        Scalar mH2O = 55.508; //molH2O/kg(l)H2O
        switch (EqIdx) {
            case pressureIdx: refValue = initPressure_;break;
            case switchIdx: refValue = injTC_ /(FluidSystem::molarMass(nCompIdx) * mH2O);break;
            case CaIdx: refValue = injCa_/(1000 * FluidSystem::molarMass(CaIdx) * mH2O);break;
            case NaIdx: refValue = (injNa_+injNaCorr_)/(1000 * FluidSystem::molarMass(NaIdx) * mH2O);break;
            case ClIdx: refValue = 2*injCa_/(1000 * FluidSystem::molarMass(CaIdx) * mH2O)
                                    + injTNH_/(1000 * FluidSystem::molarMass(TNHIdx) * mH2O)
                                    + injNa_/(1000 * FluidSystem::molarMass(NaIdx) * mH2O);break;
            case BiosuspIdx: refValue = injBiosusp_/(1000 * FluidSystem::molarMass(BiosuspIdx) * mH2O);break;
            case BiosubIdx: refValue = injSub_/(1000 * FluidSystem::molarMass(BiosubIdx) * mH2O);break;
            case O2Idx: refValue = injO2_/(1000 * FluidSystem::molarMass(O2Idx) * mH2O);break;
            case UreaIdx: refValue = injUrea_/(1000 * FluidSystem::molarMass(UreaIdx) * mH2O);break;
            case TNHIdx: refValue = injTNH_/(1000 * FluidSystem::molarMass(TNHIdx) * mH2O);break;
            case phiCalciteIdx: refValue = initPorosity_;break;
            case phiBiofilmIdx: refValue = initPorosity_;break;
        }
//        std::cout<< "reference value for EqIdx = "<<EqIdx<< ": "<<refValue<<std::endl;
        return refValue;
    }

    void postTimeStep()
    {
        // Calculate masses and flux over a layer
        //PrimaryVariables mass;
        PrimaryVariables massGas(0.0);
        PrimaryVariables massH2O(0.0);
        PrimaryVariables massBiofilm(0.0);
        PrimaryVariables massCalcite(0.0);

        double time = this->timeManager().time();
        double dt = this->timeManager().timeStepSize();

        int episodeIdx = this->timeManager().episodeIndex()-1;

//        this->model().globalPhaseStorage(massH2O, wPhaseIdx);
//        this->model().globalPhaseStorage(massGas, nPhaseIdx);
//        this->model().globalPhaseStorage(massBiofilm, bPhaseIdx);
//        this->model().globalPhaseStorage(massCalcite, cPhaseIdx);
//        this->model().globalPhaseStorage(massH2O, wPhaseIdx);
//        this->model().globalPhaseStorage(massGas, nPhaseIdx);
//        this->model().globalPhaseStorage(massBiofilm, bPhaseIdx);
//        this->model().globalPhaseStorage(massCalcite, cPhaseIdx);
////        computeStorage(PrimaryVariables &storage, int scvIdx, bool usePrevSol)
        if (this->gridView().comm().rank() == 0)
        {
//          std::cout<<"==============================================******==================================================="<<std::endl;
//          std::cout<< " MassH2O_l:   "; std::cout.width(11); std::cout<< massH2O[wCompIdx] <<" kg, "
//                     << " MassCO2_l:   "; std::cout.width(11); std::cout<< massH2O[nCompIdx] <<" kg, "
//                     << " MassBio_l:    "; std::cout.width(11); std::cout<< massH2O[BiosuspIdx] <<" kg"
//                     << " MassCa_l:    "; std::cout.width(11); std::cout<< massH2O[CaIdx] <<" kg"
//                     << " MassSub_l:    "; std::cout.width(11); std::cout<< massH2O[BiosubIdx] <<" kg"
//                     << " MassO2_l:    "; std::cout.width(11); std::cout<< massH2O[O2Idx] <<" kg"
//                     << " MassN_Urea_l:    "; std::cout.width(11); std::cout<< massH2O[UreaIdx]*2*14e-3/FluidSystem::molarMass(UreaIdx) <<" kg"
//                     << " MassN_TNH_l:    "; std::cout.width(11); std::cout<< massH2O[TNHIdx]*14e-3/FluidSystem::molarMass(TNHIdx) <<" kg"
//                     <<std::endl;
//
//            std::cout<< " MassH2O_g:   "; std::cout.width(11); std::cout << massGas[wCompIdx] << " kg, "
//                     << " MassCO2_g:   "; std::cout.width(11); std::cout << massGas[nCompIdx] << " kg, "
//                     << " MassBio_g:    "; std::cout.width(11); std::cout << massGas[BiosuspIdx] << " kg"
//                     << " MassCa_g:    "; std::cout.width(11); std::cout << massGas[CaIdx] << " kg"
//                     <<std::endl;
//
//            std::cout
//                     << " MassH2O_b:   "; std::cout.width(11); std::cout << massBiofilm[wCompIdx] << " kg, "
//                   << " MassCO2_b:   "; std::cout.width(11); std::cout << massBiofilm[nCompIdx] << " kg, "
//                   << " MassBio_b:   "; std::cout.width(11); std::cout << massBiofilm[phiBiofilmIdx] << " kg"
//                   << " MassCa_b:   "; std::cout.width(11); std::cout << massBiofilm[phiCalciteIdx] << " kg"
//                   <<std::endl;
////
//            std::cout<< " MassH2O_c:   "; std::cout.width(11); std::cout << massCalcite[wCompIdx] << " kg, "
//                   << " MassCO2_c:   "; std::cout.width(11); std::cout << massCalcite[nCompIdx]*FluidSystem::molarMass(nCompIdx)/FluidSystem::molarMass(CalciteIdx) << " kg, "
//                   << " MassBio_c:   "; std::cout.width(11); std::cout << massCalcite[phiBiofilmIdx] << " kg"
//                   << " MassCa_c:   "; std::cout.width(11); std::cout << massCalcite[phiCalciteIdx]*FluidSystem::molarMass(CaIdx)/FluidSystem::molarMass(CalciteIdx) << " kg"
//                   <<std::endl;
//
//            std::cout<< " MassH2O_Tot: "; std::cout.width(11); std::cout << massH2O[wCompIdx] + massGas[wCompIdx]<< " kg, "
//                     << " MassCO2_Tot: "; std::cout.width(11); std::cout << massH2O[nCompIdx] + massGas[nCompIdx]<< " kg, "
//                     << " MassBio_Tot:  "; std::cout.width(11); std::cout << massH2O[BiosuspIdx] +  massGas[BiosuspIdx] + massBiofilm[phiBiofilmIdx] << " kg" // + massCalcite[BiofilmIdx]<< " kg"
//                     << " MassCa_Tot:  "; std::cout.width(11); std::cout << massH2O[CaIdx] +  massGas[CaIdx] + massCalcite[phiCalciteIdx]*FluidSystem::molarMass(CaIdx)/FluidSystem::molarMass(CalciteIdx)<< " kg"
//                     << " MassN_Totl:    "; std::cout.width(11); std::cout<< massH2O[TNHIdx]*14e-3/FluidSystem::molarMass(TNHIdx) + massH2O[UreaIdx]*2*14e-3/FluidSystem::molarMass(UreaIdx)<<" kg"
//                     <<std::endl;

           std::cout<< " Time: "<<time+dt<< ", Episode: "<<episodeIdx+1<<", injection process: "<<injType_[episodeIdx]<<std::endl;
           std::cout<<"==============================================******==================================================="<<std::endl;
       }
    }

    void episodeEnd()
    {
        // Start new episode if episode is over and assign new boundary conditions
        //if(this->timeManager().episodeIndex() ==1 )


     int episodeIdx = this->timeManager().episodeIndex();
     Scalar tEpisode= EpisodeEnd(episodeIdx)-EpisodeEnd(episodeIdx-1);

        this->timeManager().startNextEpisode(tEpisode);
//            this->timeManager().setTimeStepSize(tEpisode / 100);
//        if (InjectionProcess(episodeIdx + 1) == -1)
//              this->timeManager().setTimeStepSize(0.01);
//        else if (InjectionProcess(episodeIdx + 1) == 0 || InjectionProcess(episodeIdx + 1) == 3)
                this->timeManager().setTimeStepSize(0.1);
//        else
//          this->timeManager().setTimeStepSize(10);

        std::cout<< "\n  episode number  " << episodeIdx << " done, starting next episode number  " <<episodeIdx + 1 << ", Injection scheme will be : "<<injType_[episodeIdx] << "\n"  <<std::endl;

    }

private:
    // internal method for the initial condition (reused for the
    // dirichlet conditions!)
    void initial_(PrimaryVariables &values,
                  const GlobalPosition &globalPos) const
    {
        Scalar zmax = this->bBoxMax()[1];
        values[pressureIdx] = initPressure_ ; //70e5; // - (maxHeight - globalPos[1])*densityW_*9.81; //p_atm + rho*g*h
        values[switchIdx] = initxlTC_;
        values[xlNaIdx] = initxlNa_ + xlNaCorr_;
        values[xlClIdx] = initxlCl_ + initxlTNH_ + 2*initxlCa_ + xlClCorr_;
        values[xlCaIdx] = initxlCa_;
        values[xlUreaIdx] = initxlUrea_;
        values[xlTNHIdx] = initxlTNH_;
        values[xlO2Idx] = initxlO2_;
        values[xlBiosubIdx] = initxlBiosub_;
        values[xlBiosuspIdx] = initxlBiosusp_;
        values[phiBiofilmIdx] = initBiofilm_;//0.000; // [m^3/m^3]
        values[phiCalciteIdx] = initCalcite_;//0.00000; // [m^3/m^3]

#if !ISOTHERMAL
        values[temperatureIdx] = 283.0 + (depthBOR_ - globalPos[1])*0.03;
#endif

    }
//    static const Scalar injQ (int episodeIdx) //[ml/min]
//    {
//      Scalar Q[150] = {0,
//              5,  0,  5,  0,  5,  0,
//              5,  5,  5,  0,  5,  0,
//              5,  0,  5,  0,  5,  0,
//              5,  5,  5,  0,  5,  0,
//              5,  0,  5,  0,  5,  0,
//              5,  5,  5,  0,  5,  0,
//              5,  0,  5,  0,  5,  0,
//              5,  5,  5,  0,  5,  0,
//              5,  5,  5,  0,  5,  0,
//              5,  5,  5,  0,  4,  0,
//              3.5,3.5,3.5,0,  3.5,0,
//              4,  4,  4,  0,  4,  0,
//              4,  4,  4,  0,  4,  0,
//              3.75,   3.75,   3.75, 0,    3.75,   0,
//              4,  4,  4,  0,  4,  0,
//              4,  4,  4,  0,  3.75,   0,
//              2.25,   2.25,   2.25,   0,  1,  0,
//              1,  1,  1,  0,  0.5,    0,
//              0.5,    0.5,    0,  0.15,   0,
//              0.5,    0.5,    0,  0.5,    0.5,    0,
//              0.5,    0,  2,  0,  1,  1,  0,
//
//
//      };

//      return Q[episodeIdx]/60/1e6;    //[m³/s]
//    }


//    static const int InjectionProcess (int episodeIdx)
//    {     // 2 = inoculation, 1 = ca-rich injection, -1 = no urea & no ca, 3 = urea-rich, -99 no injection
//      int Inj [150]=
//      {-99,
//      2,  -99,    3,  -99,    3,  -99,
//      -1, 1,  -1, -99,    3,  -99,
//      -1, 1,  -1, -99,    3,  -99,
//      -1, 1,  -1, -99,    3,  -99,
//      -1, 1,  -1, -99,    3,  -99,
//      -1, 1,  -1, -99,    3,  -99,
//      -1, 1,  -1, -99,    3,  -99,
//      -1, 1,  -1, -99,    3,  -99,
//      -1, 1,  -1, -99,    3,  -99,
//      -1, 1,  -1, -99,    3,  -99,
//      -1, 1,  -1, -99,    3,  -99,
//      -1, 1,  -1, -99,    3,  -99,
//      -1, 1,  -1, -99,    3,  -99,
//      -1, 1,  -1, -99,    3,  -99,
//      -1, 1,  -1, -99,    3,  -99,
//      -1, 1,  -1, -99,    3,  -99,
//      -1, 1,  -1, -99,    3,  -99,
//      -1, 1,  -1, -99,    3,  -99,
//      -1, 1,  -99,    3,  -99,
//      -1, 1,  -99,    -1, 1,  -99,
//      3,  -99,    3,  -99,    -1, 1,  -99,
//      -99};
//
//    return Inj[episodeIdx];
//    }
//    static const
    Scalar EpisodeEnd (int episodeIdx)
    {
//      //End times of the episodes in hours.
//       Scalar EpiEnd[150] = {0,   //10e20};                                                                           //0
//
//               0.1333333333,  4.55,   4.82,   20.267, 20.537, //inoculation//growth stage 1//growth stage 2
//               44.383,    44.6496666667,  44.9163333333,  44.9183333333,  51.767, //ca-pulse  1
//               52.0336666667, 68.417, 68.6836666667,  68.9503333333,  68.9523333333,  76.9,
//               77.1666666667, 97.283, 97.5496666667,  97.8163333333,  97.8183333333,  120.7,
//               120.9666666667,    140.3,  140.5666666667, 140.8333333333, 140.8353333333, 148.617,
//               148.8836666667,    164.583,    164.8496666667, 165.1163333333, 165.1183333333, 172.567,
//               172.8336666667,    188.6,  188.8666666667, 189.1333333333, 189.1353333333, 197.567,
//               197.8336666667,    212.6,  212.8666666667, 213.1333333333, 213.1353333333, 219.75,
//               220.0166666667,    236.583,    236.8496666667, 237.1163333333, 237.1183333333, 244.967,
//               245.2336666667,    260.733,    260.9996666667, 261.2663333333, 261.2683333333, 287.017,
//               287.3503333333,    308.2,  308.580952381,  308.9619047619, 308.9647619048, 316.917,
//               317.297952381, 332.5,  332.8333333333, 333.1666666667, 333.1691666667, 360.383,
//               360.7163333333,    380.35, 380.6833333333, 381.0166666667, 381.0191666667, 388.9,
//               389.2333333333,    404.733,    405.0885555556, 405.4441111111, 405.4467777778, 428.783,
//               429.1385555556,    435.583,    435.9163333333, 436.2496666667, 436.2521666667, 453.383,
//               453.7163333333,    476.383,    476.7163333333, 477.0496666667, 477.0521666667, 484.87,
//               485.2255555556,    500.717,    501.3095925926, 501.9021851852, 501.9066296296, 508.117,
//               509.4503333333,    524.25, 525.5833333333, 526.9166666667, 526.9266666667, 532.517,
//               535.1836666667,    548.35, 550.7333333333, 553.4, 556.1,   556.9444444444, 572.2,                          //113
//               574.5633333333,    576.8866666667, 601.82, 603.4633333333, 605.49, 650.57,
//               652.3633333333,    866.43, 868.1008333333, 884.77, 885.3966666667, 886.7716666667, 892.4,
//       10e10};
//    return 60 * 60 * EpiEnd[episodeIdx];

            if(episodeIdx < epiEnd_.size())
            return 60 * 60 * epiEnd_[episodeIdx]; //epiEnd from parameter file in hours!!!!
        else                            //security default value
            return 10e10;

    }

//    static constexpr Scalar dtmax_ = 200; // [s]//hier willkürlich, Anozie hat für die Säulenexperimente auf Tepisodemin/2 begrenzt!
    static constexpr Scalar eps_ = 1e-6;
//    static constexpr Scalar densityW_ = 1087; // rhow=1087;
//
//    static constexpr Scalar initxlTC_ = 2.3864e-7;        // [mol/mol]
//    static constexpr Scalar initxlNa_ = 0;
//    static constexpr Scalar initxlCl_ = 0;
//    static constexpr Scalar initxlCa_ = 0;
//    static constexpr Scalar initxlUrea_ = 0;
//    static constexpr Scalar initxlTNH_ = 3.341641e-3;
//    static constexpr Scalar initxlO2_ = 4.4686e-6;
//    static constexpr Scalar initxlBiosub_ = 2.97638e-4;
//    static constexpr Scalar initxlBiosusp_ = 0;
//    static constexpr Scalar xlNaCorr_ = 2.9466e-6;
//    static constexpr Scalar xlClCorr_ = 0;
//
//    static constexpr Scalar injTC_ = 5.8e-7;              // [kg/kg]
//    static constexpr Scalar injNa_ = 0.00379;             // [kg/m³]
//    static constexpr Scalar injCa_ = 13.3593333333;           // [kg/m³]      //computed from 0.333mol/l CaCl2
//    static constexpr Scalar injUrea_ = 20;                    // [kg/m³]
//    static constexpr Scalar injTNH_ = 3.183840574;//3.184;                // [kg/m³]      //computed from 10 g/l NH4Cl
//    static constexpr Scalar injO2_ = 0.008;                   // [kg/m³]
//    static constexpr Scalar injSub_ = 3;                  // [kg/m³]
//    static constexpr Scalar injBiosusp_ = 0.0675;         // [kg/m³]      //2.7e8 cfu/ml (40e8cfu/ml~1g/l)

    Scalar dtmax_;

    Scalar initPressure_;
    Scalar densityW_;//1087; // rhow=1087;

    Scalar initxlTC_;//2.3864e-7;       // [mol/mol]
    Scalar initxlNa_;//0;
    Scalar initxlCl_;//0;
    Scalar initxlCa_;//0;
    Scalar initxlUrea_;//0;
    Scalar initxlTNH_;//3.341641e-3;
    Scalar initxlO2_;//4.4686e-6;
    Scalar initxlBiosub_;//2.97638e-4;
    Scalar initxlBiosusp_;//0;
    Scalar xlNaCorr_;//2.9466e-6;
    Scalar xlClCorr_;//0;

    Scalar initBiofilm_;
    Scalar initCalcite_;

    Scalar initPorosity_;

    Scalar injTC_;//5.8e-7;             // [kg/kg]
    Scalar injNa_;//0.00379;                // [kg/m³]
    Scalar injCa_;//13.3593333333;          // [kg/m³]      //computed from 0.333mol/l CaCl2
    Scalar injUrea_;//20;                   // [kg/m³]
    Scalar injTNH_;//3.183840574;//3.184;               // [kg/m³]      //computed from 10 g/l NH4Cl
    Scalar injO2_;//0.008;                  // [kg/m³]
    Scalar injSub_;//3;                 // [kg/m³]
    Scalar injBiosusp_;//0.0675;            // [kg/m³]      //2.7e8 cfu/ml (40e8cfu/ml~1g/l)
    Scalar injNaCorr_;

    Scalar numInjections_;

    std::string injectionParameters_;

    std::vector<Scalar> epiEnd_;
    std::vector<int> injType_;
    std::vector<Scalar> injQ_;
    std::string name_;
};
} //end namespace

#endif
