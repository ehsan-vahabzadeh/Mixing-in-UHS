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
 * \brief Binary coefficients for methane and oxygen.
 */
#ifndef DUMUX_BINARY_COEFF_CH4_CH4BIO_HH
#define CH4BIO

#include <dumux/material/binarycoefficients/henryiapws.hh>
#include <dumux/material/binarycoefficients/fullermethod.hh>

#include <dumux/material/components/ch4.hh>
#include <dumux/material/components/ch4bio.hh>

namespace Dumux
{
namespace BinaryCoeff
{

/*!
 * \brief Binary coefficients for methane and oxygen.
 */
class CH4_CH4
{
public:
    /*!
     * \brief Henry coefficent \f$[N/m^2]\f$  for molecular oxygen in liquid nitrogen.
     */
    template <class Scalar>
    static Scalar henry(Scalar temperature)
    {
        DUNE_THROW(Dune::NotImplemented, "henry coefficient for oxygen in liquid methane");
    };

    /*!
     * \brief Binary diffusion coefficent [m^2/s] for molecular nitrogen and oxygen.
     *
     * \copybody fullerMethod()
     */
    template <class Scalar>
    static Scalar gasDiffCoeff(Scalar temperature, Scalar pressure)
    {
  	  using CH4 = Dumux::Components::CH4<Scalar>;
    //   using CH4BIO = Dumux::Components::CH4<Scalar>;


        // atomic diffusion volumes
        const Scalar SigmaNu[2] = { 25.14 /* CH4 */,  25.14 /* N2 */ };
        // molar masses [g/mol]
        const Scalar M[2] = { CH4::molarMass()*1e3, CH4::molarMass()*1e3 };
        return fullerMethod(M, SigmaNu, temperature, pressure);
    };

    /*!
     * \brief Diffusion coefficent [m^2/s] for molecular oxygen in liquid nitrogen.
     */
    template <class Scalar>
    static Scalar liquidDiffCoeff(Scalar temperature, Scalar pressure)
    {
        DUNE_THROW(Dune::NotImplemented, "diffusion coefficient for liquid oxygen and methane");
    };
};

}
} // end namepace

#endif
