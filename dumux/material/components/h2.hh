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
 * \ingroup Components
 * \brief Properties of pure molecular hydrogen \f$H_2\f$.
 */
#ifndef DUMUX_H2_HH
#define DUMUX_H2_HH

#include <dumux/material/idealgas.hh>

#include <cmath>

#include <dumux/material/components/base.hh>
#include <dumux/material/components/gas.hh>

namespace Dumux {
namespace Components {

/*!
 * \ingroup Components
 * \brief Properties of pure molecular hydrogen \f$H_2\f$.
 *
 * \tparam Scalar The type used for scalar values
 */
template <class Scalar>
class H2
: public Components::Base<Scalar, H2<Scalar> >
, public Components::Gas<Scalar, H2<Scalar> >
{
    using IdealGas = Dumux::IdealGas<Scalar>;
    static constexpr Scalar R = Constants<Scalar>::R;

public:
    /*!
     * \brief A human readable name for the \f$H_2\f$.
     */
    static std::string name()
    { return "H2"; }

    /*!
     * \brief The molar mass in \f$\mathrm{[kg/mol]}\f$ of molecular hydrogen.
     */
    static constexpr Scalar molarMass()
    { return 2.01588e-3; }

    /*!
     * \brief Returns the critical temperature \f$\mathrm{[K]}\f$ of molecular hydrogen.
     */
    static Scalar criticalTemperature()
    { return 33.18; /* [K] */ }

    /*!
     * \brief Returns the critical pressure \f$\mathrm{[Pa]}\f$ of molecular hydrogen.
     */
    static Scalar criticalPressure()
    { return 13.13e5; /* [N/m^2] */ }

    /*!
     * \brief Returns the critical pressure \f$\mathrm{[m3/mol]}\f$ of \f$CO_2\f$.
     */
    static Scalar criticalVolume()
    { return 0.0642e-3; /* [m3/mol] */ }
    
    /*!
     * \brief Returns the critical compressibility factor \f$\mathrm{[m3/mol]}\f$ of \f$H2\f$.
     */
    static Scalar criticalCompressibility()
    { return 0.3053; /* [-] */ }

    /*!
     * \brief Returns the temperature \f$\mathrm{[K]}\f$ at molecular hydrogen's triple point.
     */
    static Scalar tripleTemperature()
    { return 14.0; /* [K] */ }

    /*!
     * \brief Returns the acentric factor \f$\mathrm{[-]}\f$ of hydrogen
     */
    static Scalar acentricFactor()
    {return -0.215;}

    /*!
     * \brief Returns the atomic diffusion volume of hydrogen accordin to Reid
     */
    static Scalar atomicDiffusionVolume()
    {return 27.52;}

    /*!
     * \brief The vapor pressure in \f$\mathrm{[Pa]}\f$ of pure molecular hydrogen
     *        at a given temperature.
     *
     *\param temperature temperature of component in \f$\mathrm{[K]}\f$
     *
     * Taken from:
     *
     * See: R. Reid, et al. (1987, pp 208-209, 669) \cite reid1987
     *
     * \todo implement the Gomez-Thodos approach...
     */
    static Scalar vaporPressure(Scalar temperature)
    {
        if (temperature > criticalTemperature())
            return criticalPressure();
        if (temperature < tripleTemperature())
            return 0; // H2 is solid: We don't take sublimation into
                      // account

        // antoine equatuion
        const Scalar A = -7.76451;
        const Scalar B = 1.45838;
        const Scalar C = -2.77580;

        using std::exp;
        return 1e5 * exp(A - B/(temperature + C));
    }

    /*!
     * \brief The density \f$\mathrm{[kg/m^3]}\f$ of \f$H_2\f$ at a given pressure and temperature.
     *
     * \param temperature temperature of component in \f$\mathrm{[K]}\f$
     * \param pressure pressure of component in \f$\mathrm{[Pa]}\f$
     */
    static Scalar gasDensity(Scalar temperature, Scalar pressure)
    {
        // Assume an ideal gas
        return IdealGas::density(molarMass(), temperature, pressure);
    }

    /*!
     * \brief The molar density of \f$H_2\f$ in \f$\mathrm{[mol/m^3]}\f$,
     *   depending on pressure and temperature.
     * \param temperature The temperature of the gas
     * \param pressure The pressure of the gas
     */
    static Scalar gasMolarDensity(Scalar temperature, Scalar pressure)
    { return IdealGas::molarDensity(temperature, pressure); }

    /*!
     * \brief Returns true if the gas phase is assumed to be compressible
     */
    static constexpr bool gasIsCompressible()
    { return true; }

    /*!
     * \brief Returns true if the gas phase is assumed to be ideal
     */
    static constexpr bool gasIsIdeal()
    { return true; }

    /*!
     * \brief The pressure of gaseous \f$H_2\f$ in \f$\mathrm{[Pa]}\f$ at a given density and temperature.
     *
     * \param temperature temperature of component in \f$\mathrm{[K]}\f$
     * \param density density of component in \f$\mathrm{[kg/m^3]}\f$
     */
    static Scalar gasPressure(Scalar temperature, Scalar density)
    {
        // Assume an ideal gas
        return IdealGas::pressure(temperature, density/molarMass());
    }

    /*!
     * \brief Specific enthalpy \f$\mathrm{[J/kg]}\f$ of pure hydrogen gas.
     *
     * \param temperature temperature of component in \f$\mathrm{[K]}\f$
     * \param pressure pressure of component in \f$\mathrm{[Pa]}\f$
     */
    static const Scalar gasEnthalpy(Scalar temperature,
                                    Scalar pressure)
    {
        return gasHeatCapacity(temperature, pressure) * temperature;
    }

    /*!
     * \brief Specific isobaric heat capacity \f$\mathrm{[J/(kg*K)]}\f$ of pure
     *        hydrogen gas.
     *
     * This is equivalent to the partial derivative of the specific
     * enthalpy to the temperature.
     * \param T temperature of component in \f$\mathrm{[K]}\f$
     * \param pressure pressure of component in \f$\mathrm{[Pa]}\f$
     *
     * See: R. Reid, et al. (1987, pp 154, 657, 665) \cite reid1987
     */
    static const Scalar gasHeatCapacity(Scalar T,
                                        Scalar pressure)
    {
        // method of Joback
        const Scalar cpVapA = 27.14;
        const Scalar cpVapB = 9.273e-3;
        const Scalar cpVapC = -1.381e-5;
        const Scalar cpVapD = 7.645e-9;

        return
            1/molarMass()* // conversion from [J/(mol*K)] to [J/(kg*K)]
            (cpVapA + T*
              (cpVapB/2 + T*
                (cpVapC/3 + T*
                 (cpVapD/4))));
    }

    /*!
     * \brief The dynamic viscosity \f$\mathrm{[Pa*s]}\f$ of \f$H_2\f$ at a given pressure and temperature.
     *
     * \param temperature temperature of component in \f$\mathrm{[K]}\f$
     * \param pressure pressure of component in \f$\mathrm{[Pa]}\f$
     *
     * See:
     *
     * See: R. Reid, et al.: The Properties of Gases and Liquids,
     * 4th edition (1987, pp 396-397, 667) \cite reid1987 <BR>
     * 5th edition (2001, pp 9.7-9.8 (omega and V_c taken from p. A.19)) \cite poling2001
     */
    static Scalar gasViscosity(Scalar temperature, Scalar pressure)
    {
        const Scalar Tc = criticalTemperature();
        const Scalar Vc = criticalVolume()*1000000; // critical specific volume [cm^3/mol]
        const Scalar omega = acentricFactor(); // accentric factor
        const Scalar M = molarMass() * 1e3; // molar mas [g/mol]
        const Scalar dipole = 0.0; // dipole moment [debye]

        using std::sqrt;
        Scalar mu_r4 = 131.3 * dipole / sqrt(Vc * Tc);
        mu_r4 *= mu_r4;
        mu_r4 *= mu_r4;

        using std::pow;
        using std::exp;
        Scalar Fc = 1 - 0.2756*omega + 0.059035*mu_r4;
        Scalar Tstar = 1.2593 * temperature/Tc;
        Scalar Omega_v =
            1.16145*pow(Tstar, -0.14874) +
            0.52487*exp(- 0.77320*Tstar) +
            2.16178*exp(- 2.43787*Tstar);
        Scalar mu = 40.785*Fc*sqrt(M*temperature)/(pow(Vc, 2./3)*Omega_v);



        // convertion from micro poise to Pa s
        return mu/1e6 / 10;
    }

    /*!
     * \brief The dynamic viscosity \f$\mathrm{[Pa*s]}\f$ of \f$H_2\f$ at a high given pressure and temperature.
     *
     * \param temperature temperature of component in \f$\mathrm{[K]}\f$
     * \param pressure pressure of component in \f$\mathrm{[Pa]}\f$
     *
     * See:
     *
     * See: R. Reid, et al.: The Properties of Gases and Liquids,
     * 4th edition (1987, pp 396-397, 667) \cite reid1987 <BR>
     * 5th edition (2001, pp 9.7-9.8 (omega and V_c taken from p. A.19)) \cite poling2001
     * Lucas Method 
     */
    static Scalar gasViscosityHighP(Scalar temperature, Scalar pressure)
    {
        const Scalar Tc = criticalTemperature();
        const Scalar Pc = criticalPressure();
        const Scalar Zc = criticalCompressibility();
        // const Scalar Vc = criticalVolume()*1000000; // critical specific volume [cm^3/mol]
        // const Scalar omega = acentricFactor(); // accentric factor
        const Scalar M = molarMass() * 1e3; // molar mas [g/mol]
        
        Scalar a1 = 1.245e-3, a2 = 5.1726;
        Scalar b1 = 1.6553, b2 = 1.2723, c1 = 0.4489, c2 = 3.0578;
        Scalar d1 = 1.7368, d2 = 2.2310, f1 = 0.9425, f2 = -0.1853;
        Scalar ga = -0.3286, sig = -37.7332, eps = -7.6351, khi = 0.4489;  
        Scalar Tr = temperature/Tc, Pr = pressure/Pc;
        Scalar a = (a1/Tr)* std::exp(a2*std::pow(Tr,ga)); 
        Scalar b = a*(b1*Tr-b2);
        Scalar c = (c1/Tr)*exp(c2*std::pow(Tr,sig)); 
        Scalar d = (d1/Tr)*exp(d2*std::pow(Tr,eps));
        Scalar e = 1.3088; 
        Scalar f = f1*std::exp(f2* std::pow(Tr,khi));
        Scalar F0p = 1 + 30.55*(std::pow(std::abs(0.292 - Zc),1.725)) * std::abs(0.96 + 0.1 * (Tr-0.7));
        Scalar F0q = 1.22 * std::pow(0.76,0.15)*(std::pow((1 + 0.00385 * std::pow((Tr-12),2)),(1/M)));
        Scalar Z1  = ((0.807 * std::pow(Tr,0.618)) - 0.357 * std::exp(-0.449 * Tr) + 0.340 * std::exp(-4.058*Tr) + 0.018) * F0p * F0q;
        Scalar Z2  = Z1 * (1+((a *std::pow(Pr, e)) / ((b * std::pow(Pr,f))+std::pow((1+c * std::pow(Pr,d)),-1))));
        Scalar Y   = Z2 /Z1;
        Scalar FP  = (1+(F0p-1) * std::pow(Y, -3)) / F0p;
        Scalar FQ  = (1+(F0q-1) * (std::pow(Y, -1) - 0.007 * std::pow(std::log(Y), 4))) / F0q;
        Scalar exponent = 1.0/6.0; 
        Scalar Khi = 0.176 * std::pow((Tc / (std::pow(M, 3) * (std::pow(Pc*1e-5, 4)))), (exponent));
        Scalar mu  = Z2 * FP * FQ / Khi; // micro poise
        Scalar Pure_Visc = mu *1e-7; // Pa.s

        // convertion from micro poise to Pa s
        return Pure_Visc;
    }
    //Peng Robinson
    static Scalar PR(const Scalar temperature, const Scalar pressure)
    {
        Scalar Pc_mix, Tc_mix; //mixture critical temperature
        Scalar Rconst=8.314;//gas constant
        Scalar aconst = 0;
        Scalar bconst = 0;
        Scalar kappa = 0;
        Scalar alpha = 0;
        Scalar Tr = 0;

        //calculate the reduced temperature and pressure of every component
        Tr = temperature/criticalTemperature();
        Pc_mix = criticalPressure();
        Tc_mix = criticalTemperature();
        //calculate the constants for every component
        bconst= 0.0778*Rconst*criticalTemperature()/criticalPressure();
        kappa = 0.37464 + 1.54226* acentricFactor() - 0.2669*acentricFactor()*acentricFactor();
        alpha = pow(1+kappa*(1-pow(Tr,0.5)),2.0);
        aconst=0.45724*Rconst*Rconst*criticalTemperature()*criticalTemperature()/criticalPressure()*alpha;

        Scalar BIC = 0;
        Scalar dsmalladxi = 0;
        Scalar a_mix = 0;
        a_mix = sqrt(aconst*aconst)*(1-BIC);
        Scalar sumYiAmix = 0;
        sumYiAmix = a_mix;
        dsmalladxi = 2 * sqrt(aconst) * sqrt(aconst)*(1-BIC);
        Scalar am = 0;
        am = sumYiAmix;

        //calculate bm
        Scalar bm=0;
        bm = bconst;
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
        Scalar Term6 = 0, Term2 = 0, Term4 = 0, Term7 = 0, Term8 = 0;
        Scalar Term1 = 0, Term3 = 0, Term5 = 0;
        Scalar PHI = 0;
        Term6 = sqrt(8);
        Term1=(bconst/bm)*(temp-1);
        Term2=-log(temp-Bm);
        Term4=-Am/(Bm*Term6);
        Term5=(bconst/bm)-(dsmalladxi/am);
        Term7=2*temp+Bm*(2-Term6);
        Term8=2*temp+Bm*(2+Term6);
        Term3=Term4*(Term5)*log(Term7/Term8);
        PHI=exp(Term1+Term2+Term3);
        return PHI;
        // return 1;
        
    }
static Scalar z_factor(const Scalar temperature, const Scalar pressure)
    {
        Scalar Pc_mix, Tc_mix; //mixture critical temperature
        Scalar Rconst=8.314;//gas constant
        Scalar aconst = 0;
        Scalar bconst = 0;
        Scalar kappa = 0;
        Scalar alpha = 0;
        Scalar Tr = 0;

        //calculate the reduced temperature and pressure of every component
        Tr = temperature/criticalTemperature();
        Pc_mix = criticalPressure();
        Tc_mix = criticalTemperature();
        //calculate the constants for every component
        bconst= 0.0778*Rconst*criticalTemperature()/criticalPressure();
        kappa = 0.37464 + 1.54226* acentricFactor() - 0.2669*acentricFactor()*acentricFactor();
        alpha = pow(1+kappa*(1-pow(Tr,0.5)),2.0);
        aconst=0.45724*Rconst*Rconst*criticalTemperature()*criticalTemperature()/criticalPressure()*alpha;

        Scalar BIC = 0;
        Scalar dsmalladxi = 0;
        Scalar a_mix = 0;
        a_mix = sqrt(aconst*aconst)*(1-BIC);
        Scalar sumYiAmix = 0;
        sumYiAmix = a_mix;
        dsmalladxi = 2 * sqrt(aconst) * sqrt(aconst)*(1-BIC);
        Scalar am = 0;
        am = sumYiAmix;

        //calculate bm
        Scalar bm=0;
        bm = bconst;
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
        
    }     
};

} // end namespace Components

} // end namespace Dumux

#endif
