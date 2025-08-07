// -*- mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*-
// vi: set et ts=4 sw=4 sts=4:
//
// SPDX-FileCopyrightInfo: Copyright © DuMux Project contributors, see AUTHORS.md in root folder
// SPDX-License-Identifier: GPL-3.0-or-later
//
/*!
 * \file
 * \ingroup OnePNCTests
 * \brief Definition of the spatial parameters for the 1pnc problems.
 */

#ifndef DUMUX_1PNC_TEST_SPATIAL_PARAMS_HH
#define DUMUX_1PNC_TEST_SPATIAL_PARAMS_HH

#include <dumux/porousmediumflow/properties.hh>
#include <dumux/porousmediumflow/fvspatialparams1p.hh>

namespace Dumux {

/*!
 * \ingroup OnePNCTests
 * \brief Definition of the spatial parameters for the 1pnc test problems.
 */
template<class GridGeometry, class Scalar>
class OnePNCTestSpatialParams
: public FVPorousMediumFlowSpatialParamsOneP<GridGeometry, Scalar,
                             OnePNCTestSpatialParams<GridGeometry, Scalar>>
{
    using GridView = typename GridGeometry::GridView;
    using FVElementGeometry = typename GridGeometry::LocalView;
    using SubControlVolume = typename FVElementGeometry::SubControlVolume;
    using Element = typename GridView::template Codim<0>::Entity;
    using ParentType = FVPorousMediumFlowSpatialParamsOneP<GridGeometry, Scalar,
                                           OnePNCTestSpatialParams<GridGeometry, Scalar>>;

    static const int dimWorld = GridView::dimensionworld;
    using GlobalPosition = typename Dune::FieldVector<Scalar, dimWorld>;
    using DimWorldMatrix = Dune::FieldMatrix<Scalar, dimWorld, dimWorld>;

public:
    // export permeability type
    using PermeabilityType = DimWorldMatrix;

    OnePNCTestSpatialParams(std::shared_ptr<const GridGeometry> gridGeometry)
    : ParentType(gridGeometry)
    {
        referencePorosity_     = getParam<Scalar>("SpatialParams.ReferencePorosity", 0.2); //porosity without reactive solid volume fractions
        referencePermeability_ = getParam<Scalar>("SpatialParams.ReferencePermeability", 100 * 9.86923e-16);
        temperature_           = getParam<Scalar>("Problem.InitialTemperature");
    }
    /*!
     * \brief Returns the temperature within the domain.
     *
     *  \param element The finite volume element
     *  \param scv The sub-control volume
     *  \param elemSol The element solution
     */
    template<class ElementSolution>
    Scalar temperature(const Element& element,
                       const SubControlVolume& scv,
                       const ElementSolution& elemSol) const
    { return temperature_; }

    Scalar temperatureAtPos(const GlobalPosition& globalPos) const
    { return temperature_; }

    template<class ElementSolution>
    PermeabilityType permeability(const Element& element,
                        const SubControlVolume& scv,
                        const ElementSolution& elemSol) const
    {
        PermeabilityType K(0.0);
        K[0][0] = referencePermeability_;
        K[1][1] = referencePermeability_/10;
        // K[2][2] = referencePermeability_/10;
        return K;
    }

    /*!
     * \brief Defines the porosity \f$\mathrm{[-]}\f$.
     *
     * \param globalPos The global position
     */
    Scalar porosityAtPos(const GlobalPosition& globalPos) const
    { return referencePorosity_; }

private:
    Scalar referencePermeability_;
    Scalar referencePorosity_;
    Scalar temperature_;
};

} // end namespace Dumux

#endif
