// $Id$
/*****************************************************************************
 *   Copyright (C) 2008-2010 by Andreas Lauser                               *
 *   Copyright (C) 2008-2009 by Klaus Mosthaf                                *
 *   Institute of Hydraulic Engineering                                      *
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
#ifndef DUMUX_BIOMIN_SPATIAL_PARAMS_HH
#define DUMUX_BIOMIN_SPATIAL_PARAMS_HH

#include <dumux/material/spatialparams/implicitspatialparams.hh>
#include <dumux/material/fluidmatrixinteractions/2p/linearmaterial.hh>
#include <dumux/material/fluidmatrixinteractions/2p/regularizedbrookscorey.hh>
#include <dumux/material/fluidmatrixinteractions/2p/efftoabslaw.hh>


namespace Dumux
{
//forward declaration
template<class TypeTag>
class BioMinSpatialParams;

namespace Properties
{
// The spatial parameters TypeTag
NEW_TYPE_TAG(BioMinSpatialParams);

// Set the spatial parameters
SET_TYPE_PROP(BioMinSpatialParams, SpatialParams, Dumux::BioMinSpatialParams<TypeTag>);

// Set the material Law
SET_PROP(BioMinSpatialParams, MaterialLaw)
{
private:
    // define the material law which is parameterized by effective
    // saturations
    typedef typename GET_PROP_TYPE(TypeTag, Scalar) Scalar;
    typedef RegularizedBrooksCorey<Scalar> EffMaterialLaw;
public:
    // define the material law parameterized by absolute saturations
    typedef EffToAbsLaw<EffMaterialLaw> type;
};
}

/**
 * \brief Definition of the spatial parameters for the brine-co2 problem
 *
 */
template<class TypeTag>
class BioMinSpatialParams : public ImplicitSpatialParams<TypeTag>
{
    typedef ImplicitSpatialParams<TypeTag> ParentType;
    typedef typename GET_PROP_TYPE(TypeTag, Grid) Grid;
    typedef typename GET_PROP_TYPE(TypeTag, GridView) GridView;
    typedef typename GET_PROP_TYPE(TypeTag, Scalar) Scalar;
    typedef typename GET_PROP_TYPE(TypeTag, MaterialLawParams) MaterialLawParams;
    typedef typename GET_PROP_TYPE(TypeTag, FluidSystem) FluidSystem;
    typedef typename Grid::ctype CoordScalar;
    enum {
        dim=GridView::dimension,
        dimWorld=GridView::dimensionworld,
    };

//    typedef typename GET_PROP_TYPE(TypeTag, TwoPNCMinIndices)) Indices;
    enum {
        lPhaseIdx = FluidSystem::lPhaseIdx,
        gPhaseIdx = FluidSystem::gPhaseIdx,
    };

    typedef Dune::FieldVector<CoordScalar,dim> LocalPosition;
    typedef Dune::FieldVector<CoordScalar,dimWorld> GlobalPosition;
    typedef Dune::FieldVector<CoordScalar,dimWorld> Vector;
    typedef Dune::FieldMatrix<CoordScalar, dimWorld, dimWorld> Tensor;

    typedef typename GET_PROP_TYPE(TypeTag, SolutionVector) SolutionVector;

    typedef typename GET_PROP_TYPE(TypeTag, VolumeVariables) VolumeVariables;
    typedef typename GET_PROP_TYPE(TypeTag, FluxVariables) FluxVariables;
    typedef typename GET_PROP_TYPE(TypeTag, ElementVolumeVariables) ElementVolumeVariables;

    typedef typename GET_PROP_TYPE(TypeTag, FVElementGeometry) FVElementGeometry;
    typedef typename GridView::template Codim<0>::Entity Element;

public:
    BioMinSpatialParams(const GridView &gv)
        : ParentType(gv)
    {

        try
        {
        porosity_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, SpatialParams, Porosity);
        critPorosity_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, SpatialParams, CritPorosity);
        ScalarK_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, SpatialParams, Permeability);

        }
        catch (Dumux::ParameterException &e)
        {
            std::cerr << e << ". Abort!\n";
            exit(1) ;
        }
        // intrinsic permeabilities

        K_ = Scalar(0.0);
//      ScalarK_ = 3.e-14;  //initial permeability of contol core !!
//      ScalarK_ = 3.7e-14;  //initial permeability of core 25.10.2011
              for (int i = 0; i < dim; i++)
                  K_[i][i] = ScalarK_;

//        // porosity:
//                porosity_ = 0.18;
//
//                //exponent = 6
////                  critPorosity_ = 0.0431;           //data from pdf:    K_0 = 37mD,
//                                                  //                  K_end = 2,4mD,
//                                                  //                  phi_min = 0,13 (phi_0-phi_c_end-phi_f_end = 0,18 - 0,037 (- 0,013 biofilm estimated according to simulation))
//
//                //exponent = 6
////                  critPorosity_ = 0.089;            //data from pdf:    K_0 = 37mD,
//                                                  //                  K_min = 0,3mD,
//                                                  //                  phi_min = 0,13 (phi_0-phi_c_end-phi_f_end = 0,18 - 0,037 (- 0,013 biofilm estimated according to simulation))
//
//                //exponent = 3
//                critPorosity_ = 0.1080;           //data from pdf:    K_0 = 37mD,
//                                                  //                  K_end = 2,4mD,
//                                                  //                  phi_end = 0,137 (meassured end porosity and simulated end porosity (for phi_crit=0))
////                  //exponent = 3
////                  critPorosity_ = 0.0965;           //data from pdf:    K_0 = 37mD,
////                                                    //                  K_end = 2,4mD,
////                                                    //                  phi_end = 0,13 (phi_0-phi_c_end-phi_f_end = 0,18 - 0,037 (- 0,013 biofilm estimated according to simulation))
//                //exponent = 3
////                  critPorosity_ = 0.117;            //data from pdf:    K_0 = 37mD,
//                                                  //                  K_min = 0,3mD,
//                                                  //                  phi_min = 0,13 (phi_0-phi_c_end-phi_f_end = 0,18 - 0,037 (- 0,013 biofilm estimated according to simulation))
////                  critPorosity_ = 0.084081983;      //data from pdf:    K_0 = 30mD (measured permeability of control core),
//                                                  //                  K_end = 4,98mD (harmonic mean of measured end permebility of core halfs),
//                                                  //                  phi_end = 0,1368 (meassured, but maybe biofilm already decayed)

        // residual saturations
                coreMaterialParams_.setSwr(0.2);
                coreMaterialParams_.setSnr(0.05);

        // parameters for the Brooks-Corey law
                coreMaterialParams_.setPe(1e4);
                coreMaterialParams_.setLambda(2.0);
    }

    ~BioMinSpatialParams()
    {}


    /*!
     * \brief Update the spatial parameters with the flow solution
     *        after a timestep.
     *
     * \param globalSolution The global solution vector
     */
    void update(const SolutionVector &globalSolution)
    {
    };

    /*!
     * \brief Apply the intrinsic permeability tensor to a pressure
     *        potential gradient.
     *
     * \param element The current finite element
     * \param fvElemGeom The current finite volume geometry of the element
     * \param scvfIdx The index sub-control volume face where the
     *                      intrinsic velocity ought to be calculated.
     */
    const Tensor &intrinsicPermeability(const Element &element,
                                       const FVElementGeometry &fvElemGeom,
                                       int scvIdx) const
    {
            return K_;

    }
    const Scalar &intrinsicPermeabilityScalar(const Element &element,
            const FVElementGeometry &fvElemGeom,
            int scvIdx) const
    {
        return ScalarK_;

    }

    /*!
     * \brief Define the porosity \f$[-]\f$ of the spatial parameters
     *
     * \param vDat The data defined on the sub-control volume
     * \param element The finite element
     * \param fvElemGeom The finite volume geometry
     * \param scvIdx The local index of the sub-control volume where
     *                    the porosity needs to be defined
     */
    double solidity(const Element &element,
                    const FVElementGeometry &fvElemGeom,
                    int scvIdx) const
    {
            return 1 - porosity_;

    }
    const Scalar porosity(const Element &element,               //TODO sonst gibt es einen Fehler: Dune reported error: Dune::InvalidStateException [porosityAtPos:/temp/hommel/DUMUX/dumux/dumux/material/spatialparams/boxspatialparams1p.hh:167]: The spatial parameters do not provide a porosityAtPos() method.
            const FVElementGeometry &fvGeometry,
            int scvIdx) const
    {
        return porosity_;
    }
    const Scalar critPorosity(const Element &element,
            const FVElementGeometry &fvGeometry,
            int scvIdx) const
    {
        return critPorosity_;
    }
//    Scalar porosityAtPos(const GlobalPosition& globalPos) const
//    {
//        DUNE_THROW(Dune::InvalidStateException,
//                   "The spatial parameters do not provide "
//                   "a porosityAtPos() method.");
//    }
    // return the brooks-corey context depending on the position
    const MaterialLawParams& materialLawParams(const Element &element,
                                                const FVElementGeometry &fvElemGeom,
                                                int scvIdx) const
    {
            return coreMaterialParams_;
    }

    /*!
     * \brief Returns the heat capacity \f$[J/m^3 K]\f$ of the rock matrix.
     *
     * This is only required for non-isothermal models.
     *
     * \param element The finite element
     * \param fvElemGeom The finite volume geometry
     * \param scvIdx The local index of the sub-control volume where
     *                    the heat capacity needs to be defined
     */
//    double heatCapacity(const Element &element,
//                        const FVElementGeometry &fvElemGeom,
//                        int scvIdx) const
//    {
//        return
//            790 // specific heat capacity of granite [J / (kg K)]
//            * 2700 // density of granite [kg/m^3]
//            * (1 - porosity(element, fvElemGeom, scvIdx));
//    }


   /* double heatCapacity(const Element &element,
                            const FVElementGeometry &fvElemGeom, int scvIdx, Scalar phasePressure) const
        {
            return 0;
        }*/

    /*!
     * \brief Calculate the heat flux \f$[W/m^2]\f$ through the
     *        rock matrix based on the temperature gradient \f$[K / m]\f$
     *
     * This is only required for non-isothermal models.
     *
     * \param heatFlux The result vector
     * \param tempGrad The temperature gradient
     * \param element The current finite element
     * \param fvElemGeom The finite volume geometry of the current element
     * \param scvfIdx The local index of the sub-control volume face where
     *                    the matrix heat flux should be calculated
     */
//    void matrixHeatFlux(Vector &heatFlux,
//                        const FluxVariables &fluxDat,
//                        const ElementVolumeVariables &vDat,
//                        const Vector &tempGrad,
//                        const Element &element,
//                        const FVElementGeometry &fvElemGeom,
//                        int scvfIdx) const
//    {
//        static const Scalar lWater = 0.6;
//        static const Scalar lGranite = 2.8;
//
//        // arithmetic mean of the liquid saturation and the porosity
//        const int i = fvElemGeom.subContVolFace[scvfIdx].i;
//        const int j = fvElemGeom.subContVolFace[scvfIdx].j;
//        Scalar Sl = std::max(0.0, (vDat[i].saturation(lPhaseIdx) +
//                                     vDat[j].saturation(lPhaseIdx)) / 2);
//        Scalar poro = (porosity(element, fvElemGeom, i) +
//                       porosity(element, fvElemGeom, j)) / 2;
//
//        Scalar lsat = pow(lGranite, (1-poro)) * pow(lWater, poro);
//        Scalar ldry = pow(lGranite, (1-poro));
//
//        // the heat conductivity of the matrix. in general this is a
//        // tensorial value, but we assume isotropic heat conductivity.
//        Scalar heatCond = ldry + sqrt(Sl) * (ldry - lsat);
//
//        // the matrix heat flux is the negative temperature gradient
//        // times the heat conductivity.
//        heatFlux = tempGrad;
//        heatFlux *= -heatCond;
//    }

private:
//    bool isFine_(const GlobalPosition &pos) const
//       {
//      return (pos[0] > 0.015 && pos[0] < 0.035);
//       };

    Dune::FieldMatrix<Scalar,dim,dim> K_;

    Scalar porosity_;
    Scalar critPorosity_;
    Scalar ScalarK_;

    MaterialLawParams coreMaterialParams_;
};

}

#endif
