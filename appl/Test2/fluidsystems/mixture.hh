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
 * \ingroup Fluidsystems
 * \brief @copydoc Dumux::FluidSystems::H2OH2CH4CO2N2
 */
#include <cassert>
#include <iomanip>

#include <dumux/common/exceptions.hh>

#include <dumux/material/idealgas.hh>

#include <dumux/material/fluidsystems/base.hh>
#include <dumux/material/components/simpleh2o.hh>
// #include <dumux/material/components/h2o.hh>
#include <dumux/material/components/h2.hh>
#include <dumux/material/components/ch4.hh>
#include <dumux/material/components/simpleco2.hh>
#include <dumux/material/components/n2.hh>

#include <dumux/material/binarycoefficients/h2o_h2.hh>
#include <dumux/material/binarycoefficients/h2o_ch4.hh>
#include <dumux/material/binarycoefficients/h2o_co2.hh>
#include <dumux/material/binarycoefficients/h2o_n2.hh>

#include <dumux/material/binarycoefficients/h2_ch4.hh>
#include <dumux/material/binarycoefficients/h2_co2.hh>
#include <dumux/material/binarycoefficients/h2_n2.hh>


#include <dumux/material/binarycoefficients/ch4_co2.hh>
#include <dumux/material/binarycoefficients/ch4_n2.hh>


#include <dumux/material/binarycoefficients/co2_n2.hh>

#include <dumux/material/constants.hh>


#include <dumux/io/name.hh>
namespace Dumux {
namespace FluidSystems {
/*!
 * \ingroup Fluidsystems
 * \brief Policy for the H2O-H2-CH4-CO2-N2 fluid system
 */
template<bool fastButSimplifiedRelations = false>
struct MixingFluidSystemDefaultPolicy
{
    static constexpr  bool useH2ODensityAsLiquidMixtureDensity() { return fastButSimplifiedRelations; }
    static constexpr  bool useIdealGasDensity() { return fastButSimplifiedRelations; }
    // static constexpr  bool useIdealGasDensity() { return true; }
    static constexpr  bool useIdealGasHeatCapacities() { return fastButSimplifiedRelations; }
};

/*!
 * \ingroup Fluidsystems
 *
 * \brief A two-phase fluid system with two components water \f$(\mathrm{H_2O})\f$
 *        Nitrogen \f$(\mathrm{N_2})\f$ for non-equilibrium models.
 */
template <class Scalar, class Policy = MixingFluidSystemDefaultPolicy<>>
class MixingFluidSystem
    : public Base<Scalar, MixingFluidSystem<Scalar, Policy> >
{
    using ThisType = MixingFluidSystem<Scalar, Policy>;
    using Base = Dumux::FluidSystems::Base<Scalar, ThisType>;
     //! The ideal gas constant \f$\mathrm{[J/mol/K]}\f$
    static constexpr Scalar R = Constants<Scalar>::R;
    // convenience using declarations
    using IdealGas = Dumux::IdealGas<Scalar>;

public:

    using H2O = Dumux::Components::SimpleH2O<Scalar>;
    using H2 = Dumux::Components::H2<Scalar>;   
    using CO2 = Dumux::Components::SimpleCO2<Scalar>;
    using CH4 = Dumux::Components::CH4<Scalar>;
    using N2 = Dumux::Components::N2<Scalar>;    

    static constexpr int numPhases = 2; //!< Number of phases in the fluid system
    static constexpr int numComponents = 5; //!< Number of components in the fluid system

    static constexpr int liquidPhaseIdx = 0; //!< index of the liquid phase
    static constexpr int gasPhaseIdx = 1; //!< index of the gas phase
    static constexpr int phase0Idx = liquidPhaseIdx; //!< index of the first phase
    static constexpr int phase1Idx = gasPhaseIdx; //!< index of the second phase

    static constexpr int H2OIdx = 0;
    static constexpr int CH4Idx = 4;
    static constexpr int H2Idx = 2;
    static constexpr int CO2Idx = 3;
    static constexpr int N2Idx = 1;


    static constexpr int comp0Idx = H2OIdx; //!< index of the first component
    static constexpr int comp1Idx = CH4Idx; //!< index of the second component
    static constexpr int comp2Idx = CO2Idx; // secondary component
    static constexpr int comp3Idx = H2Idx; // third component
    static constexpr int comp4Idx = N2Idx;

    static constexpr int liquidCompIdx = H2OIdx; //!< index of the liquid component
    static constexpr int gasCompIdx = N2Idx; //!< index of the gas component


    /****************************************
     * Fluid phase related static parameters
     ****************************************/
    /*!
     * \brief Return the human readable name of a fluid phase
     *
     * \param phaseIdx The index of the fluid phase to consider
     */
    static std::string phaseName(int phaseIdx)
    {
        assert(0 <= phaseIdx && phaseIdx < numPhases);
        switch (phaseIdx)
        {
            case liquidPhaseIdx: return IOName::liquidPhase();
            case gasPhaseIdx: return IOName::gaseousPhase();
        }
        DUNE_THROW(Dune::InvalidStateException, "Invalid phase index " << phaseIdx);
    }

    /*!
     * \brief Returns whether the fluids are miscible
     */
    static constexpr bool isMiscible()
    { return true; }

    /*!
     * \brief Return whether a phase is gaseous
     *
     * \param phaseIdx The index of the fluid phase to consider
     */
    static constexpr bool isGas(int phaseIdx)
    {
        assert(0 <= phaseIdx && phaseIdx < numPhases);
        return phaseIdx == gasPhaseIdx;
    }

    /*!
     * \brief Returns true if and only if a fluid phase is assumed to
     *        be an ideal mixture.
     *
     * We define an ideal mixture as a fluid phase where the fugacity
     * coefficients of all components times the pressure of the phase
     * are independent on the fluid composition. This assumption is true
     * if Henry's law and Raoult's law apply. If you are unsure what
     * this function should return, it is safe to return false. The
     * only damage done will be (slightly) increased computation times
     * in some cases.
     *
     * \param phaseIdx The index of the fluid phase to consider
     */
    static bool isIdealMixture(int phaseIdx)
    {
        assert(0 <= phaseIdx && phaseIdx < numPhases);
        // we assume Henry's and Raoult's laws for the water phase and
        // and no interaction between gas molecules of different
        // components, so all phases are ideal mixtures!
        return true;
    }

    /*!
     * \brief Returns true if and only if a fluid phase is assumed to
     *        be compressible.
     *
     * Compressible means that the partial derivative of the density
     * to the fluid pressure is always larger than zero.
     *
     * \param phaseIdx The index of the fluid phase to consider
     */
    static constexpr bool isCompressible(int phaseIdx)
    {
        assert(0 <= phaseIdx && phaseIdx < numPhases);
        // gases are always compressible
        if (phaseIdx == gasPhaseIdx)
            return true;
        // the water component decides for the liquid phase...
        return H2O::liquidIsCompressible();
    }

    /*!
     * \brief Returns true if and only if a fluid phase is assumed to
     *        be an ideal gas.
     *
     * \param phaseIdx The index of the fluid phase to consider
     */
    static bool isIdealGas(int phaseIdx)
    {
        assert(0 <= phaseIdx && phaseIdx < numPhases);

        if (phaseIdx == gasPhaseIdx)
            // let the components decide
            return H2O::gasIsIdeal() && CH4::gasIsIdeal() && CO2::gasIsIdeal() && H2::gasIsIdeal()
        && N2::gasIsIdeal();
        return false; // not a gas
    }

    /****************************************
     * Component related static parameters
     ****************************************/
    /*!
     * \brief Return the human readable name of a component
     *
     * \param compIdx The index of the component to consider
     */
    static std::string componentName(int compIdx)
    {
        switch (compIdx)
        {
            case H2OIdx: return H2O::name();
            case H2Idx: return H2::name();
            case CH4Idx: return CH4::name();
            case CO2Idx: return CO2::name();
            case N2Idx: return N2::name();
        }

        DUNE_THROW(Dune::InvalidStateException, "Invalid component index " << compIdx);
    }


    /*!
     * \brief Return the molar mass of a component in \f$\mathrm{[kg/mol]}\f$.
     *
     * \param compIdx The index of the component to consider
     */
    static Scalar molarMass(int compIdx)
    {
        switch (compIdx)
        {
            case H2OIdx: return H2O::molarMass();
            case CH4Idx: return CH4::molarMass();
            case CO2Idx: return CO2::molarMass();
			case H2Idx: return H2::molarMass();
            case N2Idx: return N2::molarMass();
        };
        DUNE_THROW(Dune::InvalidStateException, "Invalid component index " << compIdx);
    }

    /*!
     * \brief Critical temperature of a component \f$\mathrm{[K]}\f$.
     *
     * \param compIdx The index of the component to consider
     */
    static Scalar criticalTemperature(int compIdx)
    {
        switch (compIdx)
        {
            case H2OIdx: return H2O::criticalTemperature();
            case CH4Idx: return CH4::criticalTemperature();
            case CO2Idx: return CO2::criticalTemperature();
			case H2Idx: return H2::criticalTemperature();
            case N2Idx: return N2::criticalTemperature();
        };
        DUNE_THROW(Dune::InvalidStateException, "Invalid component index " << compIdx);
    }

    /*!
     * \brief Critical pressure of a component \f$\mathrm{[Pa]}\f$.
     *
     * \param compIdx The index of the component to consider
     */
    static Scalar criticalPressure(int compIdx)
    {
        switch (compIdx)
        {
            case H2OIdx: return H2O::criticalPressure();
            case N2Idx: return N2::criticalPressure();
            case CO2Idx: return CO2::criticalPressure();
			case H2Idx: return H2::criticalPressure();
			case CH4Idx: return CH4::criticalPressure();
        };

        DUNE_THROW(Dune::InvalidStateException, "Invalid component index " << compIdx);
    }

    static Scalar criticalVolume(int compIdx)
    {
        switch (compIdx)
        {
            case H2OIdx: return H2O::criticalVolume();
            case N2Idx: return N2::criticalVolume();
            case CO2Idx: return CO2::criticalVolume();
			case H2Idx: return H2::criticalVolume();
			case CH4Idx: return CH4::criticalVolume();
        };

        DUNE_THROW(Dune::InvalidStateException, "Invalid component index " << compIdx);
    }


    static Scalar acentricFactor(int compIdx)
    {
        switch (compIdx)
        {
            case H2OIdx: return H2O::acentricFactor();
            case N2Idx: return N2::acentricFactor();
            case CO2Idx: return CO2::acentricFactor();
			case H2Idx: return H2::acentricFactor();
			case CH4Idx: return CH4::acentricFactor();
        };

        DUNE_THROW(Dune::InvalidStateException, "Invalid component index " << compIdx);
    }

    /*!
     * \brief Molar volume of a component at the critical point \f$\mathrm{[m^3/mol]}\f$.
     *
     * \param compIdx The index of the component to consider
     */
    static Scalar criticalMolarVolume(int compIdx)
    {
        DUNE_THROW(Dune::NotImplemented,
                   "H2OCH4CO2N2H2FluidSystem::criticalMolarVolume()");
    }

//PENG ROBINSON CUBIC EOS
    template <class FluidState>
    static Scalar zFactor(const FluidState &fluidState)
    {

        if (Policy::useIdealGasDensity())
                return 1;
        else {
            Scalar temperature = fluidState.temperature(gasPhaseIdx);
            Scalar pressure = fluidState.pressure(gasPhaseIdx);

            Scalar Pc_mix, Tc_mix; //mixture critical temperature
            Scalar Rconst=8.314;//gas constant
            Scalar aconst[numComponents];
            Scalar bconst[numComponents];
            Scalar kappa[numComponents];
            Scalar alpha[numComponents];
            Scalar Tr[numComponents];

            //calculate the reduced temperature and pressure of every component
            for (int i=0; i<numComponents; ++i){
                Tr[i]=temperature/criticalTemperature(i);
            }

            //calculate the mixture critical temperature and pressure
            for (int i=0; i<numComponents; ++i){
                Pc_mix+=fluidState.moleFraction(gasPhaseIdx, i)*criticalPressure(i);
                Tc_mix+=fluidState.moleFraction(gasPhaseIdx, i)*criticalTemperature(i);
            }

            //calculate the constants for every component
            for (int i=0; i<numComponents; ++i){
                bconst[i] = 0.0778*Rconst*criticalTemperature(i)/criticalPressure(i);
                kappa[i] = 0.37464 + 1.54226* acentricFactor(i) - 0.2669*acentricFactor(i)*acentricFactor(i);
                alpha[i] = pow(1+kappa[i]*(1-pow(Tr[i],0.5)),2.0);
                aconst[i]=0.45724*Rconst*Rconst*criticalTemperature(i)*criticalTemperature(i)/criticalPressure(i)*alpha[i];
            }



            Scalar BIC[numComponents][numComponents];
            //initialization
            for (int compIIdx=0;compIIdx<numComponents;compIIdx++){
            	for (int compJIdx=0; compJIdx<numComponents;compJIdx++){
                    if (compIIdx == H2OIdx)
                        BIC[compIIdx][compJIdx]=1;
                    else
            		    BIC[compIIdx][compJIdx]=0;
            	}
            }
            BIC[CH4Idx][N2Idx] = 0.01;
            BIC[CO2Idx][CO2Idx] = 0.01;
            BIC[N2Idx][N2Idx] = 0.00373228;

            for (int i=0; i<=numComponents;++i){
            	for (int j=numComponents; j>i; --j){
            		BIC[j][i] = BIC[i][j];
            	}
            }

            Scalar a_mix[numComponents][numComponents];
            //initialization of a(i,j) values
            for (int i=0;i<numComponents; ++i){
                for (int j=0;j<numComponents; ++j){
                    a_mix[i][j] =0;
                }
            }

            for (int i=0;i<numComponents; ++i){
                for (int j=0;j<numComponents; ++j){
                    a_mix[i][j] =sqrt(aconst[i]*aconst[j])*(1-BIC[i][j]);
                }
            }

            Scalar sumYiAmix[numComponents];

            //initialization of sigma yi*a(i,j) values
            for (int i=0; i<numComponents;++i){
                sumYiAmix[i]=0;
            }

            Scalar am=0;
            for (int i=0; i<numComponents;++i){
                for (int j=0;j<numComponents;++j){
                    sumYiAmix[i]+= fluidState.moleFraction(gasPhaseIdx,j) *a_mix[i][j];
                }
                am += fluidState.moleFraction(gasPhaseIdx,i)*sumYiAmix[i];
            }

            //calculate bm
            Scalar bm=0;
            for (int i=0; i<numComponents;++i){
                bm += fluidState.moleFraction(gasPhaseIdx,i)*bconst[i];
            }

            //calculate Am and Bm
            Scalar Am=am*pressure/(Rconst*Rconst*temperature*temperature);
            Scalar Bm = bm*pressure/(Rconst*temperature);

            //calculate roots of the cubic equation
            Scalar TwoPi = 6.2831853071;
            Scalar eps= 1e-14;
            Scalar x[3];
            Scalar a=-1+Bm;
            Scalar b=Am-3*Bm*Bm-2*Bm;
            Scalar c=-Am*Bm+Bm*Bm+Bm*Bm*Bm;

            Scalar q = (a*a - 3*b)/9;
            Scalar r = (a*(2*a*a - 9*b) + 27*c)/54;
            Scalar r2 = r*r;
            Scalar q3 = q*q*q;


            if(r2<q3){
                Scalar t=r/sqrt(q3);
                if(t<-1) t=-1;
                if(t>1) t=1;
                t = acos(t);
                a/=3; q=-2*sqrt(q);
                x[0]=q*cos(t/3)-a;
                x[1]=q*cos((t+TwoPi)/3)-a;
                x[2]=q*cos((t-TwoPi)/3)-a;
            }else{
                Scalar A,B(0);
                A = -pow(fabs(r)+sqrt(r2-q3),1./3);
                if(r<0) A = -A;
                if (A==0) {
                    B = 0;
                }else{
                    B = q/A;
                }
                // B = A==0? 0 : B=q/A;
                a/=3;
                x[0]=(A+B)-a;
                x[1]=-0.5*(A+B)-a;
                x[2]=0.5*sqrt(3.)*(A+B);
                if(fabs(x[2])<eps)
                {x[2] = x[1];}
            }
            //find the maximum root / Z-factor
            Scalar temp = 0;

            for (int i = 0; i < 3; ++i) {
                if(x[i]>temp && x[i]>0){
                    temp=x[i];
                }
            }
            return temp;
            // return 1;
        }
    }


    template <class FluidState>
    static std::vector<double> Fugacity_Coefficient(const FluidState &fluidState)
    {
        // Scalar PHI[numComponents]; 
        Scalar temperature = fluidState.temperature(gasPhaseIdx);
        Scalar pressure = fluidState.pressure(gasPhaseIdx); 
        std::vector<double> PHI(numComponents);  
        for (int i=0; i<numComponents; ++i)
            PHI[i]=0;
        if (Policy::useIdealGasDensity()){
            for (int i=0; i<numComponents; ++i)
                PHI[i]=1;
            return PHI;
        }        
        else {
            PHI[H2OIdx] = H2O::PR(temperature,pressure);
            PHI[CH4Idx] = CH4::PR(temperature,pressure);
            PHI[CO2Idx] = CO2::PR(temperature,pressure);
            PHI[N2Idx] = N2::PR(temperature,pressure);
            PHI[H2Idx] = H2::PR(temperature,pressure);
            return PHI;
        }
    }

    using Base::density;
    /*!
     * \brief Given a phase's composition, temperature, pressure, and
     *        the partial pressures of all components, return its
     *        density \f$\mathrm{[kg/m^3]}\f$.
     *
     * If Policy::useH2ODensityAsLiquidMixtureDensity() == false, we apply Eq. (7)
     * in Class et al. (2002a) \cite A3:class:2002b <BR>
     * for the liquid density.
     *
     * \param fluidState An arbitrary fluid state
     * \param phaseIdx The index of the fluid phase to consider
     */
    template <class FluidState>
    static Scalar density(const FluidState &fluidState, int phaseIdx)
    {
        Scalar temperature = fluidState.temperature(phaseIdx);
        Scalar pressure = fluidState.pressure(phaseIdx);
        // Scalar temperature = 326;
        // Scalar pressure = 20.0e5;

        switch (phaseIdx) {
        case liquidPhaseIdx:
        {
            // See: Ochs 2008
            // \todo: proper citation
            Scalar rhoWater = H2O::liquidDensity(temperature, pressure);
            Scalar cWater = rhoWater/H2O::molarMass();
            Scalar result =
                (1 -
                 fluidState.moleFraction(liquidPhaseIdx, H2Idx) -
                 fluidState.moleFraction(liquidPhaseIdx, CH4Idx) -
                 fluidState.moleFraction(liquidPhaseIdx, CO2Idx) -
                 fluidState.moleFraction(liquidPhaseIdx, N2Idx)) * rhoWater
                +
                fluidState.moleFraction(liquidPhaseIdx, H2Idx)*cWater*H2::molarMass() +
                fluidState.moleFraction(liquidPhaseIdx, CH4Idx)*cWater*CH4::molarMass() +
                fluidState.moleFraction(liquidPhaseIdx, CO2Idx)*cWater*CO2::molarMass() +
                fluidState.moleFraction(liquidPhaseIdx, N2Idx)*cWater*N2::molarMass();

            return result;
        }
        case gasPhaseIdx:
        {
            // assume ideal gas
            Scalar avgMolarMass =
                fluidState.moleFraction(gasPhaseIdx, H2OIdx)*H2O::molarMass() +
                fluidState.moleFraction(gasPhaseIdx, CH4Idx)*CH4::molarMass() +
                fluidState.moleFraction(gasPhaseIdx, H2Idx)*H2::molarMass() +
                fluidState.moleFraction(gasPhaseIdx, CO2Idx)*CO2::molarMass() +
                fluidState.moleFraction(gasPhaseIdx, N2Idx)*N2::molarMass();
            if (Policy::useIdealGasDensity())
                return IdealGas::molarDensity(temperature, pressure) * avgMolarMass;

            // return IdealGas::density(avgMolarMass, temperature, pressure)/zFactor(fluidState);
            // return IdealGas::density(avgMolarMass, temperature, pressure)/zFactor(fluidState);
            std::vector<double> PHI(numComponents);
            PHI[H2OIdx] = H2O::PR(temperature,pressure);
            PHI[CH4Idx] = CH4::PR(temperature,pressure);
            PHI[CO2Idx] = CO2::PR(temperature,pressure);
            PHI[N2Idx] = N2::PR(temperature,pressure);
            PHI[H2Idx] = H2::PR(temperature,pressure);
            Scalar density = 0;
            // for (int i=0; i<numComponents; ++i)
            //     PHI[i] = Fugacity_Coefficient(fluidState)[i];
            for (int i=0; i<numComponents; ++i){
                density += fluidState.moleFraction(gasPhaseIdx, i) * PHI[i] * avgMolarMass * pressure/(R*temperature);
            }
            return density;
            
            // return IdealGas::density(avgMolarMass, temperature, pressure);
            
        };
        }

        DUNE_THROW(Dune::InvalidStateException, "Invalid phase index " << phaseIdx);
    }

    using Base::molarDensity;
    /*!
     * \brief The molar density \f$\rho_{mol,\alpha}\f$
     *   of a fluid phase \f$\alpha\f$ in \f$\mathrm{[mol/m^3]}\f$
     *
     * The molar density for the simple relation is defined by the
     * mass density \f$\rho_\alpha\f$ and the molar mass of the main component
     *
     * The molar density for the complrex relation is defined by the
     * mass density \f$\rho_\alpha\f$ and the mean molar mass \f$\overline M_\alpha\f$:
     *
     * \f[\rho_{mol,\alpha} = \frac{\rho_\alpha}{\overline M_\alpha} \;.\f]
     */
    template <class FluidState>
    static Scalar molarDensity(const FluidState &fluidState, int phaseIdx)
    {
        assert(0 <= phaseIdx  && phaseIdx < numPhases);

        Scalar T = fluidState.temperature(phaseIdx);
        Scalar p = fluidState.pressure(phaseIdx);

        // liquid phase
        if (phaseIdx == liquidPhaseIdx)
        {
            // assume pure water or that each gas molecule displaces exactly one
            // molecule in the liquid.
            return H2O::liquidMolarDensity(T, p);
        }
        else
        {
            if (Policy::useIdealGasDensity())
            {   //assume ideal gas
                return IdealGas::molarDensity(T,p);
            }
            Scalar molarDensity_real=0;
            Scalar avgMolarMass =
                fluidState.moleFraction(gasPhaseIdx, H2OIdx)*H2O::molarMass() +
                fluidState.moleFraction(gasPhaseIdx, CH4Idx)*CH4::molarMass() +
                fluidState.moleFraction(gasPhaseIdx, H2Idx)*H2::molarMass() +
                fluidState.moleFraction(gasPhaseIdx, CO2Idx)*CO2::molarMass() +
                fluidState.moleFraction(gasPhaseIdx, N2Idx)*N2::molarMass();

            // molarDensity_real= fluidState.density(gasPhaseIdx)/avgMolarMass;
            std::vector<double> PHI(numComponents);
            Scalar density = 0;
            // for (int i=0; i<numComponents; ++i)
            PHI[H2OIdx] = H2O::PR(T,p);
            PHI[CH4Idx] = CH4::PR(T,p);
            PHI[CO2Idx] = CO2::PR(T,p);
            PHI[N2Idx] = N2::PR(T,p);
            PHI[H2Idx] = H2::PR(T,p);    
            for (int i=0; i<numComponents; ++i){
                // PHI[i] = Fugacity_Coefficient(fluidState)[i];
                molarDensity_real += fluidState.moleFraction(gasPhaseIdx, i) * PHI[i] * p/(R*T);
            }
            return molarDensity_real;
        }
    }

    using Base::viscosity;
    /*!
     * \brief Calculate the dynamic viscosity of a fluid phase \f$\mathrm{[Pa*s]}\f$
     *
     * Compositional effects in the gas phase are accounted by the Wilke method.
     * See Reid et al. (1987)  \cite reid1987 <BR>
     * 4th edition, McGraw-Hill, 1987, 407-410
     * 5th edition, McGraw-Hill, 20001, p. 9.21/22
     * \note Compositional effects for a liquid mixture have to be implemented.
     *
     * \param fluidState An arbitrary fluid state
     * \param phaseIdx The index of the fluid phase to consider
     */
    template <class FluidState>
    static Scalar viscosity(const FluidState &fluidState, int phaseIdx)
    {
        assert(0 <= phaseIdx  && phaseIdx < numPhases);
		Scalar temperature = fluidState.temperature(phaseIdx);
		Scalar pressure = fluidState.pressure(phaseIdx);
        // Scalar temperature = 326;
        // Scalar pressure = 20.0e5;


        if (phaseIdx == liquidPhaseIdx)

            // assume pure water for the liquid phase
            // TODO: viscosity of mixture
            return H2O::liquidViscosity(temperature, pressure);
        else {
            /* Wilke method. See:
             *
             * S.O.Ochs: "Development of a multiphase multicomponent
             * model for PEMFC - Technical report: IRTG-NUPUS",
             * University of Stuttgart, 2008
             *
             * and:
             *
             * See: R. Reid, et al.: The Properties of Gases and Liquids, 4th
             * edition, McGraw-Hill, 1987, 407-410
             */
            // Wilke method (Reid et al.):
            Scalar muResult = 0;
            const Scalar mu[numComponents] = {
                h2oGasViscosityInMixture(temperature, pressure),
                H2::gasViscosity(temperature, pressure),
                N2::gasViscosity(temperature, pressure),
                CH4::gasViscosity(temperature, pressure),
                CO2::gasViscosity(temperature, pressure)
            };

            Scalar sumx = 0.0;
            using std::max;
            for (int compIdx = 0; compIdx < numComponents; ++compIdx)
                sumx += fluidState.moleFraction(phaseIdx, compIdx);
            sumx = max(1e-10, sumx);

            for (int i = 0; i < numComponents; ++i) {
                Scalar divisor = 0;
                using std::pow;
                using std::sqrt;
                for (int j = 0; j < numComponents; ++j) {
                    Scalar phiIJ = 1 + sqrt(mu[i]/mu[j]) * pow(molarMass(j)/molarMass(i), 1/4.0);
                    phiIJ *= phiIJ;
                    phiIJ /= sqrt(8*(1 + molarMass(i)/molarMass(j)));
                    divisor += fluidState.moleFraction(phaseIdx, j)/sumx * phiIJ;
                }
                muResult += fluidState.moleFraction(phaseIdx, i)/sumx * mu[i] / divisor;
            }
            return muResult;
        }
    }

    using Base::fugacityCoefficient;
    /*!
     * \brief Calculate the fugacity coefficient \f$\mathrm{[-]}\f$ of an individual
     *        component in a fluid phase
     *
     * The fugacity coefficient \f$\mathrm{\phi^\kappa_\alpha}\f$ of
     * component \f$\mathrm{\kappa}\f$ in phase \f$\mathrm{\alpha}\f$ is connected to
     * the fugacity \f$\mathrm{f^\kappa_\alpha}\f$ and the component's mole
     * fraction \f$\mathrm{x^\kappa_\alpha}\f$ by means of the relation
     *
     * \f[
     f^\kappa_\alpha = \phi^\kappa_\alpha\;x^\kappa_\alpha\;p_\alpha
     \f]
     * where \f$\mathrm{p_\alpha}\f$ is the pressure of the fluid phase.
     *
     * The quantity "fugacity" itself is just an other way to express
     * the chemical potential \f$\mathrm{\zeta^\kappa_\alpha}\f$ of the
     * component. It is defined via
     *
     * \f[
     f^\kappa_\alpha := \exp\left\{\frac{\zeta^\kappa_\alpha}{k_B T_\alpha} \right\}
     \f]
     * where \f$\mathrm{k_B = 1.380\cdot10^{-23}\;J/K}\f$ is the Boltzmann constant.
     *
     * \param fluidState An arbitrary fluid state
     * \param phaseIdx The index of the fluid phase to consider
     * \param compIdx The index of the component to consider
     */
    template <class FluidState>
    static Scalar fugacityCoefficient(const FluidState &fluidState,
                                      int phaseIdx,
                                      int compIdx)
    {
        Scalar temperature = fluidState.temperature(phaseIdx);
        Scalar pressure = fluidState.pressure(phaseIdx);
        std::vector<double> PHI(numComponents);
        if (phaseIdx == gasPhaseIdx) {
            // PHI = Fugacity_Coefficient(fluidState);
            // Scalar fugacityCoeff = PHI[compIdx];
            Scalar fugacityCoeff = 1.0;
            // if (compIdx == H2OIdx)
            //     // For water, the fugacity coefficient is the ratio
            //     // between the density of an ideal gas and the real
            //     // density. (all other components are assumed to be an
            //     // ideal gas here.)
            //     return H2O::vaporPressure(temperature)/pressure;
            //     fugacityCoeff =
            //         IdealGas::density(H2O::molarMass(),
            //                           temperature,
            //                           pressure)
            //         /
            //         H2O::gasDensity(temperature, pressure);

            return fugacityCoeff;
            // return 0;
        }

        switch (compIdx) {
            // case H2OIdx: return H2O::vaporPressure(temperature)/pressure;
            case H2OIdx: return 1e-7;
            // case CH4Idx: return BinaryCoeff::H2O_CH4::henry(temperature)/pressure;
            case CH4Idx: return 1e7;
            // case H2Idx: return BinaryCoeff::H2O_H2::henry(temperature)/pressure;
            case H2Idx: return 1e7;
            // case CO2Idx: return BinaryCoeff::H2O_CO2::henry(temperature)/pressure;
            case CO2Idx: return 1e7;
            // case N2Idx: return BinaryCoeff::H2O_N2::henry(temperature)/pressure;
            case N2Idx: return 1e7;
        };

        DUNE_THROW(Dune::InvalidStateException, "Invalid component index " << compIdx);
    }

    using Base::diffusionCoefficient;
    /*!
     * \brief Calculate the molecular diffusion coefficient for a
     *        component in a fluid phase \f$\mathrm{[mol^2 * s / (kg*m^3)]}\f$
     *
     * Molecular diffusion of a compoent \f$\mathrm{\kappa}\f$ is caused by a
     * gradient of the chemical potential and follows the law
     *
     * \f[ J = - D \mathbf{grad} \mu_\kappa \f]
     *
     * where \f$\mathrm{\mu_\kappa}\f$ is the component's chemical potential,
     * \f$\mathrm{D}\f$ is the diffusion coefficient and \f$\mathrm{J}\f$ is the
     * diffusive flux. \f$\mathrm{mu_\kappa}\f$ is connected to the component's
     * fugacity \f$\mathrm{f_\kappa}\f$ by the relation
     *
     * \f[ \mu_\kappa = R T_\alpha \mathrm{ln} \frac{f_\kappa}{p_\alpha} \f]
     *
     * where \f$p_\alpha\f$ and \f$T_\alpha\f$ are the fluid phase'
     * pressure and temperature.
     *
     * \param fluidState An arbitrary fluid state
     * \param phaseIdx The index of the fluid phase to consider
     * \param compIdx The index of the component to consider
     */
    template <class FluidState>
    static Scalar diffusionCoefficient(const FluidState &fluidState,
                                       int phaseIdx,
                                       int compIdx)
    {
        DUNE_THROW(Dune::NotImplemented, "Diffusion coefficients");
    }

    using Base::binaryDiffusionCoefficient;
    /*!
     * \brief Given a phase's composition, temperature and pressure,
     *        return the binary diffusion coefficient \f$\mathrm{[m^2/s]}\f$ for components
     *        \f$i\f$ and \f$j\f$ in this phase.
     *
     * \param fluidState An arbitrary fluid state
     * \param phaseIdx The index of the fluid phase to consider
     * \param compIIdx The index of the first component to consider
     * \param compJIdx The index of the second component to consider
     */
    template <class FluidState>
    static Scalar binaryDiffusionCoefficient(const FluidState &fluidState,
                                             int phaseIdx,
                                             int compIIdx,
                                             int compJIdx)

    {
        Scalar temperature = fluidState.temperature(phaseIdx);
        Scalar pressure = fluidState.pressure(phaseIdx);
        

        if (compIIdx > compJIdx)
            std::swap(compIIdx, compJIdx);

        auto mole_frac_H2O = fluidState.moleFraction(phaseIdx,H2OIdx);
        auto mole_frac_CH4 = fluidState.moleFraction(phaseIdx,CH4Idx);
        auto mole_frac_H2 = fluidState.moleFraction(phaseIdx,H2Idx);
        auto mole_frac_CO2 = fluidState.moleFraction(phaseIdx,CO2Idx);
        auto mole_frac_N2 = fluidState.moleFraction(phaseIdx,N2Idx);
        switch (phaseIdx) {
        case liquidPhaseIdx:
            switch (compIIdx) {
            case H2OIdx:
                switch (compJIdx) {
                    case H2Idx:     return BinaryCoeff::H2O_H2::liquidDiffCoeff(temperature, pressure);
                    case CH4Idx:    return BinaryCoeff::H2O_CH4::liquidDiffCoeff(temperature, pressure);
                    case CO2Idx:    return BinaryCoeff::H2O_CO2::liquidDiffCoeff(temperature, pressure);
                    case N2Idx:     return BinaryCoeff::H2O_N2::liquidDiffCoeff(temperature, pressure);
                }
            default: return 1e-10;
            }
        case gasPhaseIdx:
                switch (compIIdx) {
                case H2OIdx:
                    switch (compJIdx) {
                        case H2Idx:     return BinaryCoeff::H2O_H2::gasDiffCoeff(temperature, pressure);
                        case CH4Idx:    return BinaryCoeff::H2O_CH4::gasDiffCoeff(temperature, pressure);
                        case CO2Idx:    return BinaryCoeff::H2O_CO2::gasDiffCoeff(temperature, pressure);
                        case N2Idx:     return BinaryCoeff::H2O_N2::gasDiffCoeff(temperature, pressure);
                        
                    }


                case CH4Idx:
                    switch (compJIdx) {
                        case CO2Idx:    return BinaryCoeff::CH4_CO2::gasDiffCoeff(temperature, pressure);
                        case H2Idx:    return BinaryCoeff::H2_CH4::gasDiffCoeff(temperature, pressure);
                        case N2Idx:     return BinaryCoeff::CH4_N2::gasDiffCoeff(temperature, pressure);
                    }

                case H2Idx:
                    switch (compJIdx) {
                        case CH4Idx:    return BinaryCoeff::H2_CH4::gasDiffCoeff(temperature, pressure);
                        // case CO2Idx:    return BinaryCoeff::H2_CO2::gasDiffCoeff(temperature, pressure);
                        case CO2Idx:    return BinaryCoeff::H2_CO2::gasDiffCoeff(temperature, pressure);
                        case N2Idx:     return BinaryCoeff::H2_N2::HighPgasDiffCoeff(temperature, pressure,mole_frac_H2,mole_frac_N2, Policy::useIdealGasDensity());
                    }


                case CO2Idx:
                    switch (compJIdx) {
                        case N2Idx:     return BinaryCoeff::CO2_N2::gasDiffCoeff(temperature, pressure);
                        case CH4Idx:    return BinaryCoeff::CH4_CO2::gasDiffCoeff(temperature, pressure);
                        // case H2Idx:    return BinaryCoeff::H2_CO2::gasDiffCoeff(temperature, pressure);
                        case H2Idx:    return BinaryCoeff::H2_CO2::gasDiffCoeff(temperature, pressure);
                    }
                case N2Idx:
                    switch (compJIdx) {
                        case CO2Idx:     return BinaryCoeff::CO2_N2::gasDiffCoeff(temperature, pressure);
                        case H2Idx:     return BinaryCoeff::H2_N2::HighPgasDiffCoeff(temperature, pressure,mole_frac_H2,mole_frac_N2, Policy::useIdealGasDensity());
                        case CH4Idx:    return BinaryCoeff::CH4_N2::gasDiffCoeff(temperature, pressure);
                    }    
                default: return 1e-9;
                }
                
            
        }

        DUNE_THROW(Dune::InvalidStateException,
                  "Binary diffusion coefficient of components "
                  << compIIdx << " and " << compJIdx
                  << " in phase " << phaseIdx << " is undefined!\n");
    }
};

} // end namespace FluidSystems

} // end namespace Dumux

// #endif
