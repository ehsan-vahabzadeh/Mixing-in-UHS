/*****************************************************************************
 *   Copyright (C) 2009 by Andreas Lauser                                    *
 *   Institute for Modelling Hydraulic and Environmental Systems             *
 *   University of Stuttgart, Germany                                        *
 *   email: <givenname>.<name>@iws.uni-stuttgart.de                          *
 *                                                                           *
 *   This program is free software: you can redistribute it and/or modify    *
 *   it under the terms of the GNU General Public License as published by    *
 *   the Free Software Foundation, either version 2 of the License, or       *
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
/*!
 * \file
 *
 * \brief Binary coefficients for water and hydrogen.
 */
#ifndef DUMUX_BINARY_COEFF_H2O_CH4_HH
#define DUMUX_BINARY_COEFF_H2O_CH4_HH

#include <dumux/material/binarycoefficients/henryiapws.hh>
#include <dumux/material/binarycoefficients/fullermethod.hh>

#include <dumux/material/components/ch4.hh>
#include <dumux/material/components/h2o.hh>

namespace Dumux
{
namespace BinaryCoeff
{

/*!
 * \brief Binary coefficients for water and hydrogen.
 */
class H2O_CH4
{
public:
    /*!
     * \brief Henry coefficent \f$[N/m^2]\f$  for molecular hydrogen in liquid water.
     *
     * See:
     *
     * IAPWS: "Guideline on the Henry's Constant and Vapor-Liquid
     * Distribution Constant for Gases in H2O and D2O at High
     * Temperatures"
     * http://www.iapws.org/relguide/HenGuide.pdf
     */
    template <class Scalar>
    static Scalar henry(Scalar temperature)
    {
        const Scalar E = 2215.6977;
        const Scalar F = -0.1089;
        const Scalar G = -6.6240;
        const Scalar H =  4.6789;
        Scalar result = henryIAPWS(E, F, G, H, temperature);
        return result;
    };

    /*!
     * \brief Binary diffusion coefficent [m^2/s] for molecular hydrogen and water steam.
     *  See:
     *
     * R. Reid et al.: "The properties of Gases and Liquids", 4th edition,
     * pp. 587-588, McGraw-Hill, 1987
     *
     * \copybody fullerMethod()
     */
    template <class Scalar>
    static Scalar gasDiffCoeff(Scalar temperature, Scalar pressure)
    {
    	using CH4 = Dumux::Components::CH4<Scalar>;
        using H2O= Dumux::Components::SimpleH2O<Scalar>;
        // using H2O= Dumux::Components::H2O<Scalar>;

        // atomic diffusion volumes
        const Scalar SigmaNu[2] = { 25.14 /* CH4 */,  13.1 /* H2O */ };
        // molar masses [g/mol]
        const Scalar M[2] = { CH4::molarMass()*1e3, H2O::molarMass()*1e3 };

        return fullerMethod(M, SigmaNu, temperature, pressure)/**1e7*/;
        //return 1.5e-9;
    };
    /*!
     * \brief Binary diffusion coefficent [m^2/s] for molecular nitrogen and oxygen.
     *
     * \copybody fullerMethod()
     */
    template <class Scalar>
    static Scalar HighPgasDiffCoeff(Scalar temperature, Scalar pressure, Scalar X1, Scalar X2)
    {
    	using Comp1= Dumux::Components::SimpleH2O<Scalar>;
        using Comp2= Dumux::Components::CH4<Scalar>;
        Scalar R=8.314;//gas constant
        using namespace std;
        Scalar Mu_low[2] = {0 , 0};
        Scalar Mu_high[2] = {0 , 0};
        Mu_low[0] = Comp1::gasViscosity(temperature,pressure); 
        Mu_low[1] = Comp2::gasViscosity(temperature,pressure); 
        Mu_high[0] = Comp1::gasViscosityHighP(temperature,pressure); 
        Mu_high[1] = Comp2::gasViscosityHighP(temperature,pressure); 
        // atomic diffusion volumes
        const Scalar SigmaNu[2] = { 25.14 /* CH4 */,  13.1 /* H2O */ };
        // molar masses [g/mol]
        const Scalar M[2] = { Comp1::molarMass()*1e3, Comp2::molarMass()*1e3 };
        const Scalar Tc[2] = { Comp1::criticalTemperature(), Comp2::criticalTemperature() };
        const Scalar Pc[2] = { Comp1::criticalPressure(), Comp2::criticalPressure() };
        const Scalar AF[2] = { Comp1::acentricFactor(), Comp2::acentricFactor() };
        Scalar Weigh_Mu_Low[2] = {0 , 0};
        Scalar Weigh_Mu_High[2] = {0 , 0};
        Scalar LowP_Diff = fullerMethod(M, SigmaNu, temperature, pressure);

        Weigh_Mu_Low[0] = pow((1.0+sqrt((Mu_low[0] / Mu_low[1])) * pow((M[1] / M[0]), 1.0/4.0)),2) / (sqrt((8 *(1+(M[0] / M[1])))));
        Weigh_Mu_Low[1] = pow((1 + sqrt((Mu_low[1] / Mu_low[0])) * pow((M[0] / M[1]), 1.0/4.0)),2) / (sqrt((8 *(1+(M[1] / M[0])))));
        Scalar LowP_Visc = Mu_low[0]/(1+(X2/X1) * Weigh_Mu_Low[0]) + Mu_low[1]/(1+(X1/X2)*Weigh_Mu_Low[1]);

        Weigh_Mu_High[0] = pow((1+sqrt((Mu_high[0] / Mu_high[1])) * pow((M[1] / M[0]), 1.0/4.0)),2) / (sqrt((8 *(1+(M[0] / M[1])))));
        Weigh_Mu_High[1] = pow((1 + sqrt((Mu_high[1] / Mu_high[0])) * pow((M[0] / M[1]), 1.0/4.0)),2) / (sqrt((8 *(1+(M[1] / M[0])))));
        Scalar HighP_Visc = Mu_high[0]/(1+(X2/X1) * Weigh_Mu_High[0]) + Mu_high[1]/(1+(X1/X2)*Weigh_Mu_High[1]);

        Scalar b = -0.27 - 0.38 *(X1 * AF[0] + X2 * AF[1]); 
        Scalar c = -0.05 + 0.1 *(X1 * AF[0] + X2 * AF[1]);
        Scalar Pr = pressure / (X1 * Pc[0] + X2 * Pc[1]);
        Scalar Visc_ratio = 1.07 * pow((LowP_Visc / HighP_Visc),(b + c * Pr)); // Low Pressure to High Pressure Viscosity Ratio

        
        Scalar real_density = (X1* Comp1::PR(temperature, pressure)  * pressure/(R*temperature)) + (X2* Comp2::PR(temperature, pressure) * pressure/(R*temperature));
        Scalar ideal_density = (X1 * pressure/(R*temperature)) + (X2* pressure/(R*temperature));
        Scalar HighP_Diff = Visc_ratio * LowP_Diff * ideal_density / real_density;


        return HighP_Diff;
    };
    /*!
     * \brief Diffusion coefficent [m^2/s] for molecular nitrogen in liquid water.
     *
     * The empirical equations for estimating the diffusion coefficient in
     * infinite solution which are presented in Reid, 1987 all show a
     * linear dependency on temperature. We thus simply scale the
     * experimentally obtained diffusion coefficient of page 610
     *
     * See:
     *
     * R. Reid et al.: "The properties of Gases and Liquids", 4th edition,
     * pp. 599, McGraw-Hill, 1987
     *
     */
    template <class Scalar>
    static Scalar liquidDiffCoeff(Scalar temperature, Scalar pressure)
    {
        const Scalar Texp = 275 /*+ 25*/; // [K]
        const Scalar Dexp = 0.85e-9; // [m^2/s]
        return Dexp * temperature/Texp;
        //return 1.5e-9;

    };
};

}
} // end namepace

#endif
