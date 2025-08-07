/*
 * bioCarbonicAcid.hh
 *
 *  Created on: 9.8.2011
 *      Author: hommel
 */

#ifndef BIO_CARBONIC_ACID_HH_
#define BIO_CARBONIC_ACID_HH_

#include <dumux/common/exceptions.hh>
#include <dumux/material/components/component.hh>
#include <dumux/material/fluidsystems/biofluidsystem.hh>
#include <dumux/implicit/2pbiomin/properties.hh>
#include <dumux/material/components/h2o.hh>

#include <cmath>
#include <iostream>
#include <dumux/common/math.hh>

namespace Dumux
{
/*!
 * \brief The equilibrium chemistry is calculated in this class. The function calculateEquilbriumChemistry is used to
 * control the Newton Solver "newton1D". The chemical functions and derivations are implemented in the private part of
 * class.
 */
template <class TypeTag, class CO2Tables>
class BioCarbonicAcid
{
    typedef typename GET_PROP_TYPE(TypeTag, Scalar) Scalar;
    typedef typename GET_PROP_TYPE(TypeTag, FluidSystem) FluidSystem;
    typedef typename GET_PROP_TYPE(TypeTag, VolumeVariables) VolumeVariables;
    typedef typename GET_PROP_TYPE(TypeTag, PrimaryVariables) PrimaryVariables;
    typedef typename GET_PROP_TYPE(TypeTag, GridView) GridView;
    typedef typename GridView::template Codim<0>::Entity Element;
    typedef typename GET_PROP_TYPE(TypeTag, FVElementGeometry) FVElementGeometry;

    typedef BioCarbonicAcid<TypeTag, CO2Tables> ThisType;
    typedef Dumux::H2O<Scalar> H2O;


public:

    BioCarbonicAcid()
{
        try
    {

        // biomass parameters
        ca1_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, BioCoefficients, ca1);
        ca2_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, BioCoefficients, ca2);
        cd1_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, BioCoefficients, cd1);
        dc0_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, BioCoefficients, dc0);
        kmue_  = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, BioCoefficients, kmue);
        F_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, BioCoefficients, F);
        Ke_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, BioCoefficients, Ke);
        KpHa_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, BioCoefficients, KpHa);
        Ks_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, BioCoefficients, Ks);
        Yield_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, BioCoefficients, Yield);

        // calcite parameters
        ac_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, CalciteCoefficients, ac);
        kdiss1_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, CalciteCoefficients, kdiss1);
        kdiss2_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, CalciteCoefficients, kdiss2);
        kprec_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, CalciteCoefficients, kprec);
        ndiss_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, CalciteCoefficients, ndiss);
        nprec_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, CalciteCoefficients, nprec);
        Asw0_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, CalciteCoefficients, Asw0);

        //ureolysis kinetic parameters
        kub_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, UreolysisCoefficients, kub);
        kurease_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, UreolysisCoefficients, kurease);
//        nub_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, UreolysisCoefficients, nub);
//        Keu1_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, UreolysisCoefficients, Keu1);
//        Keu2_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, UreolysisCoefficients, Keu2);
        KNH4_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, UreolysisCoefficients, KNH4);
        Ku_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, UreolysisCoefficients, Ku);


        plausibilityTolerance_ = GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Model, PlausibilityTolerance);
//        maxPrecipitateVolumePerTimestep_= GET_RUNTIME_PARAM_FROM_GROUP(TypeTag, Scalar, Model, maxPrecipitateVolumePerTimestep);
    }
    catch (Dumux::ParameterException &e) {
        std::cerr << e << ". Abort!\n";
        exit(1) ;
    }
}

    static const int wPhaseIdx = FluidSystem::wPhaseIdx;
    static const int nPhaseIdx = FluidSystem::nPhaseIdx;

    static const int wCompIdx = FluidSystem::wCompIdx;
    static const int nCompIdx = FluidSystem::nCompIdx;

    static const int H2OIdx = FluidSystem::H2OIdx;
    static const int CTotIdx = FluidSystem::TCIdx;
    static const int CaIdx = FluidSystem::CaIdx;
    static const int NaIdx = FluidSystem::NaIdx;
    static const int ClIdx = FluidSystem::ClIdx;
    static const int HIdx = FluidSystem::HIdx;
    static const int OHIdx = FluidSystem::OHIdx;
    static const int CO2Idx = FluidSystem::CO2Idx;
    static const int HCO3Idx = FluidSystem::HCO3Idx;
    static const int CO3Idx = FluidSystem::CO3Idx;
    static const int CalciteIdx = FluidSystem::CalciteIdx;

    static const int BiofilmIdx = FluidSystem::BiofilmIdx;
    static const int BiosuspIdx = FluidSystem::BiosuspIdx;
    static const int BiosubIdx = FluidSystem::BiosubIdx;
    static const int UreaIdx = FluidSystem::UreaIdx;
    static const int O2Idx = FluidSystem::O2Idx;

    static const int TNHIdx = FluidSystem::TNHIdx;
    static const int NH4Idx = FluidSystem::NH4Idx;

    static const int numComponents = FluidSystem::numComponents;
    static const int numMajorComponents = FluidSystem::numMajorComponents;
    static const int numSecComponents = FluidSystem::numSecComponents;
    static const int numTotComponents = numComponents + numSecComponents;
    static const int numPhases = FluidSystem::numPhases;
    static const int numSPhases = FluidSystem::numSPhases;

    static const int cPhaseIdx = FluidSystem::cPhaseIdx;
    static const int bPhaseIdx = FluidSystem::bPhaseIdx;

    static const int phiBiofilmIdx = numComponents;
    static const int phiCalciteIdx = numComponents + 1;

    typedef Dune::FieldVector<Scalar, 4> Vector;   // Ionic Strength with NH4/totalnh
//    typedef Dune::FieldVector<Scalar, 3> Vector;     // Ionic Strength without NH4/totalnh
    typedef Dune::FieldVector<Scalar, 2> SolVector;
    typedef Dune::FieldVector<Scalar, numTotComponents> CompVector;

    typedef CompositionalSecCompFluidState<Scalar, FluidSystem> FluidState;

//    template <class VolumeVariables>
//    void calculateEquilibriumChemistry(const VolumeVariables &volVars, int phaseState, Scalar constant_salinity, Scalar constant_c, CompVector &variable)
    template <class FluidState>
    void calculateEquilibriumChemistry(const FluidState &fluidState, int phaseState, Scalar constant_salinity, Scalar constant_c, CompVector &variable)
    {

        gammaCO2_ = 1.0;
        h2o_ = 55.508; //molH2O/kgH2O
        pressure_ = fluidState.pressure(wPhaseIdx);
        temperature_ = fluidState.temperature();

//        if (constant_c <= 0.0)
//        {
//          std::cout<<"  constant c in chemistry is: "<<constant_c<<" setting all molefractions to 1e-10!" <<std::endl;
//          Scalar totalMolality = h2o_;
//            variable[H2OIdx] = h2o_/ totalMolality;
//            variable[CTotIdx] = 1e-10; //calculate the mole fraction of cTot in terms of mol CO2 / mol solution
//            variable[CaIdx] = 1e-10;
//            variable[NaIdx] = 1e-10;
//            variable[ClIdx] = 1e-10;
//            variable[CO2Idx] = 1e-10;
//            variable[HCO3Idx] = 1e-10;
//            variable[CO3Idx] = 1e-10;
//            variable[BiosuspIdx] = 1e-10;
//            variable[BiosubIdx] = 1e-10;
//            variable[O2Idx] = 1e-10;
//            variable[UreaIdx] = 1e-10;
//            variable[NH4Idx] = 1e-10;
//            variable[TNHIdx] = 1e-10;
//        }
        if(phaseState == -1) //both Phases: solve an open system with co2 concentration constant
        {
            Scalar moleFracSalinity = constant_salinity;
            Scalar moleFracCO2 = constant_c;

            salinity_ = moleFracToMolality(moleFracSalinity, moleFracSalinity, moleFracCO2);

            co2_ =  (salinity_ + h2o_)/(1/moleFracCO2 - 1);
            ca_ = moleFracToMolality(variable[CaIdx], moleFracSalinity, moleFracCO2);
            na_ = moleFracToMolality(variable[NaIdx], moleFracSalinity, moleFracCO2);
            cl_ = moleFracToMolality(variable[ClIdx], moleFracSalinity, moleFracCO2);
            totalnh_ = moleFracToMolality(variable[TNHIdx], moleFracSalinity, moleFracCO2);

            if(std::isnan(ca_) || std::isinf(ca_) || ca_<0)
            {
                 std::cout<<"in chemistry ca_ is = "<< ca_ <<std::endl;
                 ca_ = 1e-10;
            }
            if(std::isnan(na_) || std::isinf(na_) || na_<0)
            {
                 std::cout<<"in chemistry na_ is: "<< na_ <<std::endl;
                 na_ = 1e-10;
            }
            if(std::isnan(cl_) || std::isinf(cl_) || cl_<0)
            {
                 std::cout<<"in chemistry cl_ is: "<< cl_ <<std::endl;
                 cl_ = 1e-10;
            }
            if(std::isnan(totalnh_) || std::isinf(totalnh_) || totalnh_<0)
            {
                std::cout<<"in chemistry totalnh_ is: "<< totalnh_ <<std::endl;
                totalnh_ = 1e-10;
            }

            Scalar m = na_ + ca_;
                Scalar Temp = fluidState.temperature();
                /* Millero et al. 2007: The dissociation of carbonic acid */
                /* in NaCl solutions as a function of concentration and temperature */

                /*for pK1*/
                Scalar a0 = 31.3616;Scalar  a1 = 0.86644;Scalar  a2 = -0.33611;Scalar  a3 = 0.05888;
                Scalar  b0 = -1422.25317; Scalar c0 = -4.84141;

//                 Scalar A = a0*sqrt(m) + a1*m+ a2*pow(m,1.5) + a3*m*m ;
                Scalar A = a0*sqrt(m) + a1*m+ a2*sqrt(m*m*m) + a3*m*m ;
//                 Scalar B = b0 * pow (m,0.5); Scalar C = c0*pow(m,0.5);
                Scalar B = b0 * sqrt(m);
                Scalar C = c0*sqrt(m);

                Scalar dpK1 = A +  B/Temp + C*log(Temp);
                Scalar pK1 = - 402.56788 + 11656.46/Temp + 72.173*log(Temp) - 0.161325*Temp + 7.5526E-5*Temp*Temp;

                pK1 = pK1 + dpK1;

                /*for pK2*/
                a0 = 36.88545; a1 = 1.66599; a2 = -0.68730; a3 = 0.12070;
                b0 = -1669.55918; c0 = -5.83555;

//                 A = a0*pow(m,0.5) + a1*m+ a2*pow(m,1.5) + a3*m*m;
                A = a0*sqrt(m) + a1*m+ a2*sqrt(m*m*m) + a3*m*m ;
//                 B = b0 * pow (m,0.5); C = c0*pow(m,0.5);
                B = b0 * sqrt(m);
                C = c0*sqrt(m);

                Scalar dpK2 = A +  B/Temp + C*log(Temp);
                Scalar  pK2 = -122.4994 + 5811.18/Temp + 20.5263*log(Temp) - 0.0120897*Temp;

                pK2 = pK2 + dpK2;

                /*Bell et al. 2008: Ammonia/ammonium dissociation coefficient*/
                /*in seawater: A significant numerical correction*/
                Scalar I_f = 0.5*(na_ + 4.*ca_ + cl_);                         /*ionic strength of salt solution: here, equivalent to m, neglecting other ions*/
                Scalar pKa = 10.0423 - 0.0315536*(Temp-273.15) + 0.14737*I_f;

                  apparentk1_ = pow (10.,-pK1);
                  apparentk2_ = pow (10.,-pK2);
                  apparentka_ = pow (10.,-pKa);

            initH_ = 1e-5; //Initial guess
            Scalar activityH = initH_;

            //Anozies apparent constants
            k1_ = apparentk1_;
            k2_ = apparentk2_;
            ka_ = apparentka_;
            kw_ = constW(pressure_, temperature_);

            Scalar tolAbs = 1e-20;
            Scalar tolRel = 1e-15;
            int maxIter = 30;

            //Do the Newton iteration and calculate the components molalities and update the mass fraction array and
            //the concentration of the changed primary variables
            if(newton1D(activityH, &ThisType::H_CO2, tolAbs, tolRel, maxIter) == false) //Alex' Newton
//            if(newton1D(activityH, tolAbs, maxIter) == false) //Anozies Newton
            {
                initH_ = 1e-5;
                activityH = initH_;
                Scalar a0 = 0.0;
                Scalar b0 = 1e-1;
                Scalar tol = 1e-15;
                if(bisection1D(activityH, &ThisType::H_CO2, a0, b0, tol) == false) //Alex' bisection
//                if(bisection1D(tol) == false) //Anozies bisection
                {
                    DUNE_THROW(Dune::InvalidStateException, "in Chemistry: Bisection did not converge!" );
                }
            }
                H_CO2(activityH); //update component molalities

                //update mole fractions in the variable vector for the open system

                cTot_ = co2_ + hco3_ + co3_; //calculate the molality of cTot from the other c-components


//                  Scalar massFracCTot = molalityToMassFrac(cTot_, FluidSystem::molarMass(CTotIdx), massFracSalinity, massFracCO2);
                  Scalar moleFracCTot = molalityToMoleFrac(cTot_, moleFracSalinity, moleFracCO2);

                  Scalar biosusp = moleFracToMolality(variable[BiosuspIdx], moleFracSalinity, moleFracCTot);
                  if(std::isnan(biosusp) || std::isinf(biosusp) || biosusp<0)
                {
                    std::cout<<"in chemistry suspended biomass is: "<< biosusp <<std::endl;
                    biosusp = 1e-10;
                }
                Scalar biosub = moleFracToMolality(variable[BiosubIdx], moleFracSalinity, moleFracCTot);
                if(std::isnan(biosub) || std::isinf(biosub) || biosub<0)
                {
                    std::cout<<"in chemistry biosubstrate is: "<< biosub <<std::endl;
                    biosub = 1e-10;
                }
                Scalar urea = moleFracToMolality(variable[UreaIdx], moleFracSalinity, moleFracCTot);
                if(std::isnan(urea) || std::isinf(urea) || urea<0)
                {
      //                std::cout<<"  moleFrac Urea in chemistry is: "<< moleFracUrea << ", mFSalinity, mFCTot: "<<moleFracSalinity<<","<<moleFracCTot <<std::endl;
                    std::cout<<"in chemistry urea is: "<< urea <<std::endl;
                    urea = 1e-10;
                }
                Scalar o2 = moleFracToMolality(variable[O2Idx], moleFracSalinity, moleFracCTot);
                if(std::isnan(o2) || std::isinf(o2) || o2<0)
                {
                    std::cout<<"in chemistry o2 is: "<< o2 <<std::endl;
                    o2 = 1e-10;
                }

                  Scalar totalMolality = h2o_ + cTot_ + na_ + cl_ + ca_ + totalnh_ + urea + biosusp + biosub + o2;
                  variable[H2OIdx] = h2o_/totalMolality;
                  variable[CTotIdx] = cTot_/totalMolality; //calculate the mole fraction of cTot in terms of mol CO2 / mol solution
                  variable[CaIdx] = ca_/totalMolality;
                  variable[NaIdx] = na_/totalMolality;
                  variable[ClIdx] = cl_/totalMolality;
                  variable[CO2Idx] = co2_/totalMolality;
                  variable[HCO3Idx] = hco3_/totalMolality;
                  variable[CO3Idx] = co3_/totalMolality;
                  variable[TNHIdx] = totalnh_/totalMolality;
                  variable[NH4Idx] = nh4_/totalMolality;
                  variable[BiosuspIdx] = biosusp/totalMolality;
                  variable[BiosubIdx] = biosub/totalMolality;
                  variable[UreaIdx] = urea/totalMolality;
                  variable[O2Idx] = o2/totalMolality;
                  variable[OHIdx] = oh_/totalMolality;
                  variable[HIdx] = h_/totalMolality;

        }

        else //lPhaseOnly: solve a closed system with cTot concentration constant
        {
            Scalar moleFracCTot = constant_c;
            Scalar moleFracSalinity = constant_salinity;
            if(moleFracSalinity<0.0)
            {
                 std::cout<<"in chemistry moleFracSalinity is negative: "<< moleFracSalinity <<std::endl;
                 moleFracSalinity = 1e-10;
            }

            salinity_ = moleFracToMolality(moleFracSalinity,  moleFracSalinity, moleFracCTot);
            cTot_ =  moleFracToMolality(moleFracCTot, moleFracSalinity, moleFracCTot);
            ca_ = moleFracToMolality(variable[CaIdx], moleFracSalinity, moleFracCTot);
            if(std::isnan(ca_) || std::isinf(ca_) || ca_<0)
            {
                 std::cout<<"in chemistry ca_ is = "<< ca_ <<std::endl;
//               std::cout<<" moleFracCTot = "<< moleFracCTot <<std::endl;
//               std::cout<<" moleFracSalinity = "<< moleFracSalinity <<std::endl;
                 ca_ = 1e-10;
            }
            na_ = moleFracToMolality(variable[NaIdx], moleFracSalinity, moleFracCTot);
            if(std::isnan(na_) || std::isinf(na_) || na_<0)
            {
                 std::cout<<"in chemistry na_ is: "<< na_ <<std::endl;
//               std::cout<<" moleFracCTot = "<< moleFracCTot <<std::endl;
//               std::cout<<" moleFracSalinity = "<< moleFracSalinity <<std::endl;
                 na_ = 1e-10;
            }
            cl_ = moleFracToMolality(variable[ClIdx],  moleFracSalinity, moleFracCTot);
            if(std::isnan(cl_) || std::isinf(cl_) || cl_<0)
            {
                 std::cout<<"in chemistry cl_ is: "<< cl_ <<std::endl;
//               std::cout<<" moleFracCTot = "<< moleFracCTot <<std::endl;
//               std::cout<<" moleFracSalinity = "<< moleFracSalinity <<std::endl;
                 cl_ = 1e-10;
            }
            totalnh_ = moleFracToMolality(variable[TNHIdx], moleFracSalinity, moleFracCTot);
            if(std::isnan(totalnh_) || std::isinf(totalnh_) || totalnh_<0)
            {
                std::cout<<"in chemistry totalnh_ is: "<< totalnh_ <<std::endl;
//                  std::cout<<" moleFracCTot = "<< moleFracCTot <<std::endl;
//                  std::cout<<" moleFracSalinity = "<< moleFracSalinity <<std::endl;
                totalnh_ = 1e-10;
            }

            Scalar m = na_ + ca_;
                Scalar Temp = fluidState.temperature();
                /* Millero et al. 2007: The dissociation of carbonic acid */
                /* in NaCl solutions as a function of concentration and temperature */

                /*for pK1*/
                Scalar a0 = 31.3616;Scalar  a1 = 0.86644;Scalar  a2 = -0.33611;Scalar  a3 = 0.05888;
                Scalar  b0 = -1422.25317; Scalar c0 = -4.84141;

//                 Scalar A = a0*sqrt(m) + a1*m+ a2*pow(m,1.5) + a3*m*m ;
                Scalar A = a0*sqrt(m) + a1*m+ a2*sqrt(m*m*m) + a3*m*m ;
//                 Scalar B = b0 * pow (m,0.5); Scalar C = c0*pow(m,0.5);
                Scalar B = b0 * sqrt(m);
                Scalar C = c0*sqrt(m);

                Scalar dpK1 = A +  B/Temp + C*log(Temp);
                Scalar pK1 = - 402.56788 + 11656.46/Temp + 72.173*log(Temp) - 0.161325*Temp + 7.5526E-5*Temp*Temp;

                pK1 = pK1 + dpK1;

                /*for pK2*/
                a0 = 36.88545; a1 = 1.66599; a2 = -0.68730; a3 = 0.12070;
                b0 = -1669.55918; c0 = -5.83555;

//                 A = a0*pow(m,0.5) + a1*m+ a2*pow(m,1.5) + a3*m*m;
                A = a0*sqrt(m) + a1*m+ a2*sqrt(m*m*m) + a3*m*m ;
//                 B = b0 * pow (m,0.5); C = c0*pow(m,0.5);
                B = b0 * sqrt(m);
                C = c0*sqrt(m);

                Scalar dpK2 = A +  B/Temp + C*log(Temp);
                Scalar  pK2 = -122.4994 + 5811.18/Temp + 20.5263*log(Temp) - 0.0120897*Temp;

                pK2 = pK2 + dpK2;

                /*Bell et al. 2008: Ammonia/ammonium dissociation coefficient*/
                /*in seawater: A significant numerical correction*/
                Scalar I_f = 0.5*(na_ + 4.*ca_ + cl_);                         /*ionic strength of salt solution: here, equivalent to m, neglecting other ions*/
                Scalar pKa = 10.0423 - 0.0315536*(Temp-273.15) + 0.14737*I_f;

                  apparentk1_ = pow (10.,-pK1);
                  apparentk2_ = pow (10.,-pK2);
                  apparentka_ = pow (10.,-pKa);

//            molality_[0] =  na_;              //the Debüe-Hückel-equation is no longer used, instead, the empirical relations above are implemented!
//            molality_[1] = cl_;
//            molality_[2] = ca_;
//            molality_[3] =  totalnh_;
//            charge_[0] = FluidSystem::charge(NaIdx);
//            charge_[1] = FluidSystem::charge(ClIdx);
//            charge_[2] = FluidSystem::charge(CaIdx);
//            charge_[3] = FluidSystem::charge(NH4Idx);
//            ionicStrength();
//            gammaH_ = activityCoefficient(ionicStrength_, temperature_, HIdx);
//            gammaOH_ = activityCoefficient(ionicStrength_, temperature_, OHIdx);
//            gammaHCO3_ = activityCoefficient(ionicStrength_, temperature_, HCO3Idx);
//            gammaCO3_ = activityCoefficient(ionicStrength_, temperature_, CO3Idx);
//            gammaNH3_ = activityCoefficient(ionicStrength_, temperature_, TNHIdx);
//            gammaNH4_ = activityCoefficient(ionicStrength_, temperature_, NH4Idx);
//            gammaCO2_ = 1;
//            k1_ = const1(pressure_, temperature_)*gammaCO2_/gammaHCO3_/gammaH_;
//            k2_ = const2(pressure_, temperature_)*gammaHCO3_/gammaH_/gammaCO3_;
//            //kgg_ = solubilityProductCaCO(pressure_, temperature_)/gammaCa_/gammaCO3_;
//            kw_ = constW(pressure_, temperature_)/gammaH_/gammaOH_;
//            ka_ = consta(pressure_, temperature_)*gammaNH4_/gammaH_/gammaNH3_;
            //Anozies apparent constants
            k1_ = apparentk1_;
            k2_ = apparentk2_;
            ka_ = apparentka_;
            kw_ = constW(pressure_, temperature_);

            //Parameters for the newton solver
//            Scalar CTotLow = 1e-4;
//            Scalar CTotHigh = 1e-2;
            Scalar tolAbs = 1e-20; //1e-11;old
            Scalar tolRel = 1e-20; //1e-11;old
            int maxIter = 40;
            initH_ = 1e-7;
            Scalar activityH = initH_;
            if(newton1D(activityH, &ThisType::H_Ctot, tolAbs, tolRel, maxIter) == true) //Alex' Newton
//          if(newton1D(activityH, tolAbs, maxIter) == true)  //Anozies Newton
            {
                //update all component molalities
                H_Ctot(activityH);
            }
            else //solve with the bisection method and hco3 as primary variable
            {
                Scalar a0 = 0;
                Scalar b0 = 1e-3;//1e-4; old
//                initH_ = 1e-5;
                Scalar tol = 1e-12;//1e-8; old
                Scalar activityH = b0;
                if(bisection1D(activityH, &ThisType::H_Ctot, a0, b0, tol) == true) //Alex' Bisection
//                if(bisection1D(tol) == true) //Anozies Bisection
                {
                    H_Ctot(activityH);//   CTot_HCO3(activityHCO3); //update all component molalities
                }
                else
                {
                    DUNE_THROW(Dune::InvalidStateException, "in Chemistry: Bisection did not converge!" );
                }

            }

            Scalar biosusp = moleFracToMolality(variable[BiosuspIdx], moleFracSalinity, moleFracCTot);
            if(std::isnan(biosusp) || std::isinf(biosusp) || biosusp<0)
            {
                std::cout<<"in chemistry suspendedbiomass is: "<< biosusp <<std::endl;
                biosusp = 1e-10;
            }
            Scalar biosub = moleFracToMolality(variable[BiosubIdx], moleFracSalinity, moleFracCTot);
            if(std::isnan(biosub) || std::isinf(biosub) || biosub<0)
            {
                std::cout<<"in chemistry biosubstrate is: "<< biosub <<std::endl;
                biosub = 1e-10;
            }
            Scalar urea = moleFracToMolality(variable[UreaIdx], moleFracSalinity, moleFracCTot);
            if(std::isnan(urea) || std::isinf(urea) || urea<0)
            {
                std::cout<<"in chemistry urea is: "<< urea <<std::endl;
                urea = 1e-10;
            }
            Scalar o2 = moleFracToMolality(variable[O2Idx], moleFracSalinity, moleFracCTot);
            if(std::isnan(o2) || std::isinf(o2) || o2<0)
            {
                std::cout<<"in chemistry o2 is: "<< o2 <<std::endl;
                o2 = 1e-10;
            }

//            Scalar totalMolality = h2o_ + cTot_ + na_ + cl_ + ca_ + totalnh_ + urea + biosusp + biosub + o2;
            Scalar totalMolality = h2o_ + cTot_ + na_ + cl_ + ca_;
            if(std::isnan(totalMolality))
            {
                 std::cout<<"---------------  totalMolality in chemistry is nan!! "<<std::endl;
            }


            variable[H2OIdx] = h2o_/totalMolality;
            variable[CTotIdx] = cTot_/totalMolality; //calculate the mole fraction of cTot in terms of mol CO2 / mol solution
            variable[CaIdx] = ca_/totalMolality;
            variable[NaIdx] = na_/totalMolality;
            variable[ClIdx] = cl_/totalMolality;
            variable[CO2Idx] = co2_/totalMolality;
            variable[HCO3Idx] = hco3_/totalMolality;
            variable[CO3Idx] = co3_/totalMolality;
            variable[TNHIdx] = totalnh_/totalMolality;
            variable[NH4Idx] = nh4_/totalMolality;
            variable[BiosuspIdx] = biosusp/totalMolality;
            variable[BiosubIdx] = biosub/totalMolality;
            variable[UreaIdx] = urea/totalMolality;
            variable[O2Idx] = o2/totalMolality;
            variable[OHIdx] = oh_/totalMolality;
            variable[HIdx] = h_/totalMolality;

            Scalar f = na_ + h_ + 2*ca_ - oh_ - hco3_ - 2*co3_ - cl_ + nh4_;
            Scalar fmolfrac = 2*variable[CaIdx] + variable[NaIdx] + variable[NH4Idx] + variable[HIdx] - variable[ClIdx] - variable[HCO3Idx] - 2*variable[CO3Idx] - variable[OHIdx];

            for (int i = 0; i < numComponents + numSecComponents; ++i)
            {
                if(std::isnan(variable[i]))
                {
                     std::cout<<"  moleFrac of  "<< FluidSystem::componentName(i) << " in chemistry is: "<< variable[i]<<std::endl;
                }
            }
            for (int i = 0; i < numComponents + numSecComponents; ++i)
            {
                if(variable[i]<0)
                {
                     std::cout<<"  moleFrac of  "<< FluidSystem::componentName(i) << " in chemistry is: "<< variable[i]<<std::endl;
                }
            }

        }

                      std::stringstream  message ;

                      // mass Check
                      const Scalar eps = plausibilityTolerance_ ;
                      for (int compIdx=0; compIdx< numComponents+numSecComponents; ++ compIdx){
                          const Scalar xTest = variable[compIdx];

                          if (not std::isfinite(xTest) or xTest < 0.-eps or xTest > 1.+eps ){
                              message <<"\nUnphysical Value in Mass: \n";

                              message << "\tx" <<"_w"
                                      <<"^"<<FluidSystem::componentName(compIdx)<<"="
                                      << variable[compIdx] <<"\n";
                          }
                      }

                      // Some check wrote into the error-message, add some additional information and throw
                      if (not message.str().empty()){

                          message << "salinity = " <<constant_salinity<< "\n";
                          message << "ctotal = " <<constant_c<< "\n";
//                          message << "totalMolality = " << totalMolality << "\n";

                          message << " all other mole fractions:" << "\n" ;
                          for(unsigned int compIdx=0; compIdx< numComponents+numSecComponents; ++ compIdx){
                              message << "moleFraction[" << compIdx << "]=" << variable[compIdx] << "\n";
                          }
                          DUNE_THROW(NumericalProblem, message.str());
                      }

    }

    //Return equlibrium constant for chemical equation:
    //H2CO3 <--> H + HCO3
    static Scalar const1(const Scalar pw, const Scalar T)
    {
        return(pow(10,-6.3));
    }

    //Return equlibrium constant for chemical equation:
    //HCO3 <--> H + CO3
    static Scalar const2(const Scalar pw, const Scalar T)
    {
        return(pow(10,-10.3));
    }

//    Return equlibrium constant for dissolution reaction:
//    CaCO3(s) <--> Ca + CO3
    static Scalar solubilityProductCaCO(const Scalar pw, const Scalar T)
    {
//        Scalar k2_fw = 6.5e-7; //molCaCO/m3/s
//        Scalar k2_bw = 1.9e2; //molCaCO/m3/s
//        Scalar Kgg = k2_fw/k2_bw;
//        return Kgg;
        return(4.8e-9);
    }

    //Return equlibrium constant for chemical equation:
    // H2O <--> H + OH
    static Scalar constW(const Scalar pw, const Scalar T)
    {
        return(1e-14);
    }
    //Return equlibrium constant for chemical equation:
    // NH4 <--> H + NH3
    /*static*/ Scalar consta(const Scalar pw, const Scalar T)
    {
        return(pow(10,-9.29)); //pow(10,-9.25)
    }


    static Scalar massFracToMolality(const Scalar massFracX, const Scalar molarMassX, const Scalar massFracSalinity,
            const Scalar massFracC)
    {
        Scalar molalityX = massFracX/molarMassX/(1- massFracSalinity - massFracC);
        return molalityX;
    }


    /*!
     * \brief Returns the mass fraction of a component x (kg x / kg solution) for a given
     * molality fraction (mol x / mol solution)
     * The salinity and the mole Fraction of CO2 are considered
     *
     */

    static Scalar molalityToMassFrac(Scalar molalityX, Scalar molarMassX, Scalar massFracSalinity, Scalar massFracCTot)
    {
        Scalar massFracX = molalityX * molarMassX * (1 - massFracSalinity - massFracCTot);
        return massFracX;
    }


    static Scalar moleFracToMolality(Scalar moleFracX, Scalar moleFracSalinity, Scalar moleFracCTot)
    {
        Scalar molalityX = moleFracX / (1 - moleFracSalinity - moleFracCTot) / FluidSystem::molarMass(H2OIdx);
        return molalityX;
    }

    static Scalar molalityToMoleFrac(Scalar molalityX, Scalar moleFracSalinity, Scalar moleFracCTot)
    {
        Scalar moleFracX = molalityX * (1 - moleFracSalinity - moleFracCTot) * FluidSystem::molarMass(H2OIdx);
        return moleFracX;
    }


    /*!
     * \brief The ionic strength of a substance is calculated only with the salinity until now!
     */

    static Scalar ionicStrength(Scalar molalitySalinity)
    {
        Scalar ionicStrength = 0.0;
        //Scalar Product
        for (int compIdx = 0; compIdx < 2; ++compIdx)
        {
            ionicStrength += molalitySalinity;
        }
        ionicStrength *= 0.5;

        return ionicStrength;
    }
    static Scalar ionicStrength(Scalar mNa, Scalar mCl, Scalar mCa, Scalar mNH4 )
    {
        Scalar ionicStrength = 0.5*( mNa    * FluidSystem::charge(NaIdx) * FluidSystem::charge(NaIdx)
        + mCl   * FluidSystem::charge(ClIdx) * FluidSystem::charge(ClIdx)
        + mCa   * FluidSystem::charge(CaIdx) * FluidSystem::charge(CaIdx)
        + mNH4  * FluidSystem::charge(NH4Idx) * FluidSystem::charge(NH4Idx));

        return ionicStrength;
    }
    static Scalar ionicStrength(Scalar mNa, Scalar mCl, Scalar mCa )
    {
        Scalar ionicStrength = 0.5*( mNa    * FluidSystem::charge(NaIdx) * FluidSystem::charge(NaIdx)
        + mCl   * FluidSystem::charge(ClIdx) * FluidSystem::charge(ClIdx)
        + mCa   * FluidSystem::charge(CaIdx) * FluidSystem::charge(CaIdx));

        return ionicStrength;
    }

    void ionicStrength()
    {
        ionicStrength_ = 0.0;
        //Scalar Product
        for (int compIdx = 0; compIdx < 4; ++compIdx)
//        for (int compIdx = 0; compIdx < 3; ++compIdx)
        {
            ionicStrength_ += molality_[compIdx] * charge_[compIdx] * charge_[compIdx];
        }
        ionicStrength_ *= 0.5;
    }

    //Calculates the activity with a modified Debye-Hückel equation after Parkhurst (1990) for
    //ionic strengths up to 2.
    static Scalar activityCoefficient(Scalar ionicStrength, Scalar temperatureK, int compIdx)
    {
        if (ionicStrength<0)
        {
            ionicStrength = 0;
        }
//        Scalar temperatureC = temperatureK - 273.15; //Temperature in °C
//        //some sort of density
//        Scalar d = 1 - pow((temperatureC - 3.9863), 2)*(temperatureC + 288.9414)/(508929.2*(temperatureC + 68.12963))
//                +  0.011445*exp(-374.3 / temperatureC);
//        //dielectric constant
//        Scalar eps = 2727.586 + 0.6224107*temperatureK - 466.9151*log(temperatureK) - 52000.87/temperatureK;
        //A, B are temperature dependent parameters for the Debye-Hückel equation
//        Scalar A = 1.82483e6 * sqrt(d)/pow(eps*temperatureK, 1.5);
//        Scalar B = 50.2916*sqrt(d)/pow(eps*temperatureK, 0.5);
        Scalar charge = FluidSystem::charge(compIdx);
        Scalar ai = FluidSystem::ai(compIdx);
        Scalar bi = FluidSystem::bi(compIdx);
        Scalar A = 0.5085;
        Scalar B = 0.3285e10;
        // The actual modified Debye Hückel equation
        Scalar logActivityCoefficient = -A*(charge*charge)*sqrt(ionicStrength)/(1 + B*ai*sqrt(ionicStrength))
                + bi*ionicStrength;

        return pow(10, logActivityCoefficient);
//          return 1.0;
    }

    static Scalar J(Scalar x)
    {

      Scalar c[5], res;

      /*Pitzer 1974, Thermodaynamics of Electrolytes V*/

      c[1]=4.581;  c[2]=0.7237;  c[3]=0.0120;  c[4]=0.528;

      res = x/(4. + c[1]*pow(x,-c[2])*exp(-c[3]*pow(x,c[4])));


      return(res);
    }
    static Scalar Jprime(Scalar x)
    {

      Scalar res, eps;

      eps = 1.E-3;

      res = (J(x+eps) - J(x))/eps;


      return(res);
    }

    static Scalar Appa_Ksp(Scalar mNa, Scalar mCa, Scalar mNH4, Scalar mHCO3, Scalar mCO3, Scalar mCl, Scalar temp)
    {

      Scalar f, B_cacl, C_cacl, B1_cacl, I, sqrt_I, gamma_Ca, gamma_CO3, Ksp;
      Scalar beta_cacl_0, beta_cacl_1, C_cacl_phi;
      Scalar beta_nacl_0, beta_nacl_1, C_nacl_phi;
      Scalar beta_nahco3_0, beta_nahco3_1, C_nahco3_phi;
      Scalar beta_naco3_0, beta_naco3_1, C_naco3_phi;
      Scalar psi_canacl, psi_co3nacl, theta_naca, theta_clco3;
      Scalar B1_nacl, C_nacl, B1_nahco3, C_nahco3, B1_naco3, C_naco3, B_naco3;
      Scalar A_phi, a[6], T,x_clco3,x_clcl, x_co3co3,x_cana,x_caca,x_nana;
      Scalar E_theta_cana, E_theta_clco3, E1_theta_cana, E1_theta_clco3;

      Scalar beta_nh4cl_0, beta_nh4cl_1, beta_nh4co3_0, beta_nh4co3_1, beta_nh4hco3_0, beta_nh4hco3_1; /*new*/
      Scalar B_nh4cl, B_nh4co3, B_nh4hco3, B1_nh4cl, B1_nh4co3, B1_nh4hco3, C_nh4cl, C_nh4co3, C_nh4cl_phi, C_nh4co3_phi; /*new*/

      I = 0.5*( mNa + 4.*mCa + mNH4 + mHCO3 + 4*mCO3 + mCl) + 1.E-20;
      sqrt_I = sqrt(I);

      T = temp;
      a[0]=-8.1765300E-1; a[1]=-8.6852760E-1; a[2]=1.9251000E+4; a[3]=5.2514840E-3; a[4]=-7.1493970E-6; a[5]=9.3385590E-12;

      A_phi = a[0] + a[1]/(T-222.) + a[2]/(T*T) + a[3]*T + a[4]*T*T + a[5]*T*T*T*T;
      /*MODELING AND NUMERICAL SIMULATION OF SALT TRANSPORT AND PHASE TRANSITIONS IN UNSATURATED POROUS BUILDING MATERIALS By Andreas Nicolai*/

      beta_cacl_0 = 0.3159;  beta_cacl_1 = 1.614; C_cacl_phi = -0.00034;
      beta_nacl_0 = 0.0765; beta_nacl_1 = 0.2664; C_nacl_phi = 0.00127;
      beta_nahco3_0 = 0.0277; beta_nahco3_1 = 0.0411; C_nahco3_phi = 0.0;
      beta_naco3_0 = 0.1898; beta_naco3_1 = 0.846; C_naco3_phi = -0.048;
      psi_canacl = -0.014; psi_co3nacl = 0.016;
      theta_naca = 0.07; theta_clco3 = -0.053;


      beta_nh4co3_0 = 0.1288; beta_nh4co3_1 = 1.433; C_nh4co3_phi = 0.0005; /*new*/
      beta_nh4hco3_0 = -0.038; beta_nh4hco3_1 = 0.07;                       /*new*/
      beta_nh4cl_0 = 0.0522; beta_nh4cl_1 = 0.1918; C_nh4cl_phi = 0.003;    /*new*/


      x_clco3 = 6.*(-1.)*(-2.)*A_phi*sqrt_I;
      x_clcl = 6.*(-1.)*(-1.)*A_phi*sqrt_I;
      x_co3co3 = 6.*(-2.)*(-2.)*A_phi*sqrt_I;
      x_cana = 6.*(+2.)*(+1.)*A_phi*sqrt_I;
      x_caca = 6.*(+2.)*(+2.)*A_phi*sqrt_I;
      x_nana = 6.*(+1.)*(+1.)*A_phi*sqrt_I;


      E_theta_cana = ((+2.)*(+1.)/(4.*I))*( J(x_cana) - 0.5*J(x_caca) - 0.5*J(x_nana) );
      E_theta_clco3 = ((-1.)*(-2.)/(4.*I))*( J(x_clco3) - 0.5*J(x_clcl) - 0.5*J(x_co3co3) );

      E1_theta_cana = -(E_theta_cana/I) + ((+2)*(+1)/(8*I*I))*( x_cana*Jprime(x_cana) - 0.5*x_caca*Jprime(x_caca) - 0.5*x_nana*Jprime(x_nana) );
      E1_theta_clco3 = -(E_theta_clco3/I) + ((-1)*(-2)/(8*I*I))*( x_clco3*Jprime(x_clco3) - 0.5*x_clcl*Jprime(x_clcl) - 0.5*x_co3co3*Jprime(x_co3co3) );

        f = -A_phi * ( sqrt_I/(1. + 1.2*sqrt_I) + (2./1.2)*log(1. + 1.2*sqrt_I) );
        B_cacl = beta_cacl_0 + (beta_cacl_1 / (2.*I)) * (1. - exp(-2.*sqrt_I) * (1. + 2.*sqrt_I));
        B1_cacl = (beta_cacl_1 / (2.*I*I)) * ( -1. + exp(-2.*sqrt_I) * ( 1. + 2.*sqrt_I + 2.*I));
//         C_cacl = C_cacl_phi  / (2.*pow ( (2.*1.) , 0.5 ));
        C_cacl = C_cacl_phi  / (2.*sqrt(2.*1.));

        B1_nacl = (beta_nacl_1 / (2.*I*I)) * ( -1. + exp(-2.*sqrt_I) * ( 1. + 2.*sqrt_I + 2.*I));
//         C_nacl = C_nacl_phi  / (2.*pow ( (1.*1.) , 0.5 ));
        C_nacl = C_nacl_phi  / (2.*sqrt(1.*1.));

        B1_nahco3 = (beta_nahco3_1 / (2.*I*I)) * ( -1. + exp(-2.*sqrt_I) * ( 1. + 2.*sqrt_I + 2.*I));
//         C_nahco3 = C_nahco3_phi  / (2.*pow ( (1.*1.) , 0.5 ));
        C_nahco3 = C_nahco3_phi  / (2.*sqrt(1.*1.));

        B_naco3 = beta_naco3_0 + (beta_naco3_1 / (2.*I)) * (1. - exp(-2.*sqrt_I) * (1. + 2.*sqrt_I));
        B1_naco3 = (beta_naco3_1 / (2.*I*I)) * ( -1. + exp(-2.*sqrt_I) * ( 1. + 2.*sqrt_I + 2.*I));
//         C_naco3 = C_naco3_phi  / (2.*pow ( (1.*2.) , 0.5 ));
        C_naco3 = C_naco3_phi  / (2.*sqrt(1.*2.));


        B_nh4cl = beta_nh4cl_0 + (beta_nh4cl_1 / (2.*I)) * (1. - exp(-2.*sqrt_I) * (1. + 2.*sqrt_I));  /*new*/
        B1_nh4cl = (beta_nh4cl_1 / (2.*I*I)) * ( -1. + exp(-2.*sqrt_I) * ( 1. + 2.*sqrt_I + 2.*I));    /*new*/
//         C_nh4cl = C_nh4cl_phi  / (2.*pow ( (2.*1.) , 0.5 ));       /*new*/
        C_nh4cl = C_nh4cl_phi  / (2.*sqrt(2.*1.));                                         /*new*/

        B_nh4co3 = beta_nh4co3_0 + (beta_nh4co3_1 / (2.*I)) * (1. - exp(-2.*sqrt_I) * (1. + 2.*sqrt_I));  /*new*/
        B1_nh4co3 = (beta_nh4co3_1 / (2.*I*I)) * ( -1. + exp(-2.*sqrt_I) * ( 1. + 2.*sqrt_I + 2.*I));      /*new*/
//         C_nh4co3 = C_nh4co3_phi  / (2.*pow ( (1.*2.) , 0.5 ));
        C_nh4co3 = C_nh4co3_phi  / (2.*sqrt(1.*2.));                                          /*new*/

        B_nh4hco3 = beta_nh4hco3_0 + (beta_nh4hco3_1 / (2.*I)) * (1. - exp(-2.*sqrt_I) * (1. + 2.*sqrt_I));  /*new*/
        B1_nh4hco3 = (beta_nh4hco3_1 / (2.*I*I)) * ( -1. + exp(-2.*sqrt_I) * ( 1. + 2.*sqrt_I + 2.*I));      /*new*/



        gamma_Ca = exp (
                4.*f
                + mCl*(2.*B_cacl + mCl*C_cacl)
                + mNa*mCl*(4.*B1_nacl + 2.*C_nacl)
                + mNa*mHCO3*(4.*B1_nahco3 + 2.*C_nahco3)
                + mNa*mCO3*(4.*B1_naco3 + 2.*C_naco3)
                + mCa*mCl*(4.*B1_cacl + 2.*C_cacl)

                        + mNH4*mCl*(4.*B1_nh4cl + 2.*C_nh4cl)        /*new*/
                        + mNH4*mHCO3*(4.*B1_nh4hco3)  /*new*/
                        + mNH4*mCO3*(4.*B1_nh4co3 + 2.*C_nh4co3)     /*new*/


                + mNa*(2.*theta_naca + 2.*E_theta_cana + mCl*psi_canacl)
                + 4.*mNa*mCa*E1_theta_cana + 4.*mCl*mCO3*E1_theta_clco3
                );
        gamma_CO3 = exp (
                 4.*f
                 + mNa*(2.*B_naco3 + mNa*C_naco3)
                 + mNa*mCl*(4.*B1_nacl + 2.*C_nacl)
                 + mNa*mHCO3*(4.*B1_nahco3 + 2.*C_nahco3)
                 + mNa*mCO3*(4.*B1_naco3 + 2.*C_naco3)

                         + mNH4*(2.*B_nh4co3 + mNH4*C_nh4co3)        /*new*/
                         + mNH4*mCl*(4.*B1_nh4cl + 2.*C_nh4cl)        /*new*/
                         + mNH4*mHCO3*(4.*B1_nh4hco3)                /*new*/
                         + mNH4*mCO3*(4.*B1_nh4co3 + 2.*C_nh4co3)       /*new*/

                 + mCa*mCl*(4.*B1_cacl + 2.*C_cacl)
                 + mCl*(2.*theta_clco3 + 2.*E_theta_clco3 + mNa*psi_co3nacl)
                 + 4.*mNa*mCa*E1_theta_cana + 4.*mCl*mCO3*E1_theta_clco3
                 );

//        Ksp = pow (10.,-8.48)/(gamma_Ca*gamma_CO3);
        Ksp = 3.31131e-9/(gamma_Ca*gamma_CO3);
      return(Ksp);
    }

//    Scalar pH(const VolumeVariables &volVars)
//    {
//      Scalar mH = moleFracToMolality(volVars.moleFraction(wPhaseIdx,HIdx), volVars.moleFracSalinity(), volVars.moleFraction(wPhaseIdx,nCompIdx));  //[mol_H/kg_H2O]
//      Scalar pH = -log10(mH);
//          return pH;
//    }
    Scalar Omega(const Scalar mNa,
            const Scalar mCa,
            const Scalar mNH4,
            const Scalar mHCO3,
            const Scalar mCO3,
            const Scalar mCl,
            const Scalar temperature)
    {
     Scalar Ksp = Appa_Ksp( mNa,  mCa,  mNH4,  mHCO3,  mCO3,  mCl, temperature);
     Scalar Omega_ = mCa * mCO3 / Ksp;
     return Omega_;
    }
    Scalar OmegaApprox(const Scalar mCa,
            const Scalar mCO3)
    {
     Scalar Omega_ = mCa * mCO3 / 3.31131e-9; // = 3.3e-9= Ksp(Standard) = pow (10.,-8.48);
     return Omega_;
    }
    Scalar rdiss(const Scalar initialPorosity,
            const Scalar volFracCalcite,
            const Scalar mNa,
            const Scalar mCa,
            const Scalar mNH4,
            const Scalar mHCO3,
            const Scalar mCO3,
            const Scalar mCl,
            const Scalar temperature,
            const Scalar mH)
    {
        Scalar Asw = Asw0_ * cbrt((1-volFracCalcite/initialPorosity)*(1-volFracCalcite/initialPorosity));   // TODO Asw should be a function of Sw, too!
        if (Asw < 1e-8 || isnan(Asw))
        {
            std::cout<< "Asw = "<<Asw<<std::endl;
            Asw = 0;
            std::cout<< "Asw, corrected = "<<Asw<<std::endl;
        }
        Scalar Acw = ac_ * volFracCalcite;
        if (ac_ * volFracCalcite > Asw)
            Acw = Asw;
        Scalar rdiss_ = 0;
        Scalar Omega_ = Omega(mNa,  mCa,  mNH4,  mHCO3,  mCO3,  mCl, temperature);
        if (Omega_ <= 1)
        {
              rdiss_ = (kdiss1_ * mH + kdiss2_) * Acw * pow((1 - Omega_),ndiss_); //[mol/dm³s]
              rdiss_ *= 1000; // rdiss [mol/m³s]
        }

        return rdiss_;
    }
    Scalar rprec(const Scalar initialPorosity,
            const Scalar volFracCalcite,
            const Scalar mNa,
            const Scalar mCa,
            const Scalar mNH4,
            const Scalar mHCO3,
            const Scalar mCO3,
            const Scalar mCl,
            const Scalar temperature)
    {
        Scalar Asw = Asw0_ * cbrt((1-volFracCalcite/initialPorosity)*(1-volFracCalcite/initialPorosity));   // TODO Asw should be a function of Sw, too!
        if (Asw < 1e-8 || std::isnan(Asw))
             {
                 std::cout<< "Asw = "<<Asw<<std::endl;
                 Asw = 0;
                 std::cout<< "Asw, corrected = "<<Asw<<std::endl;
             }
             Scalar rprec_ = 0;
             Scalar Omega_ = Omega(mNa,  mCa,  mNH4,  mHCO3,  mCO3,  mCl, temperature);
             if (Omega_ >= 1)
             {
                 rprec_ = kprec_ * Asw * pow(Omega_ - 1 , nprec_);//[mol/dm³s]
                 rprec_ *= 1000; // rprec [mol/m³s]
             }


        return rprec_;
    }
    Scalar rurea(const Scalar mUrea,
            const Scalar densityBiofilm,
            const Scalar volFracBiofilm,
            const Scalar mNH4)
    {
       // compute rate of urealysis:
       //    Scalar vmax = kurease_ / (1 + mH/Keu1_ +Keu2_/mH); //[molurea/(kgurease s)]

         Scalar vmax = kurease_; //According to new experimental results without pH dependence
         Scalar Zub = kub_ *  densityBiofilm * volFracBiofilm; // new nub =1!  pow(densityBiofilm * volFracBiofilm,nub_);        // [kgurease/m³]
       //            Scalar Zub = kub_ *  pow(massBiofilm,0.5);     // [kgurease/m³]
         //      Scalar Zub = kub_ *  pow(0.01,nub_);           //= Zub (volFracBiofilm = const = 0.001)
         Scalar rurea_ = vmax * Zub * mUrea / ((Ku_ + mUrea) * (1 + mNH4 / KNH4_)); //[mol/m³s]

        return rurea_;
    }
    Scalar ra(const Scalar cBio, const Scalar volFracBiofilm, const Scalar porosity, const Scalar Sw)
    {
     // compute attachment coefficient and rate:
     Scalar ka = ca1_ * volFracBiofilm + ca2_;          //[1/s]
     Scalar ra_ = ka * porosity * Sw * cBio;

        return ra_;
    }
    Scalar rd(const Scalar densityBiofilm,
            const Scalar volFracBiofilm,
            const Scalar initialPorosity,
            const Scalar porosity,
            const Scalar Sw,
            const Scalar absgradpw,
            const Scalar volFracCalcite,
            const Scalar cO2,
            const Scalar cSubstrate)
    {
        Scalar cd2 =  volFracBiofilm / (initialPorosity - volFracCalcite);      //[-]
        Scalar kd = cd1_ * pow((porosity * Sw * absgradpw),0.58) + cd2 * mue(cO2, cSubstrate);  //[1/s]
        Scalar rd_ = kd * densityBiofilm * volFracBiofilm;
        return rd_;
    }
    Scalar mue(const Scalar cO2,
            const Scalar cSubstrate)
    {
        //compute biomass growth coefficient and rate
             Scalar mue_ = kmue_ * cSubstrate / (Ks_ + cSubstrate) * cO2 / (Ke_ + cO2);// [1/s]

        return mue_;
    }
    Scalar rgb(const Scalar cBio,
            const Scalar porosity,
            const Scalar Sw,
            const Scalar cO2,
            const Scalar cSubstrate)
    {
         Scalar rgb_ = mue(cO2, cSubstrate) * porosity * Sw * cBio; //[kg/m³s]

        return rgb_;
    }
    Scalar rgf(const Scalar densityBiofilm,
            const Scalar volFracBiofilm,
            const Scalar cO2,
            const Scalar cSubstrate)
    {
        Scalar rgf_ = mue(cO2, cSubstrate) * densityBiofilm * volFracBiofilm;               //[kg/m³s]

        return rgf_;
    }
    Scalar rdcb(const Scalar cBio,
            const Scalar porosity,
            const Scalar Sw,
            const Scalar mH)
    {
         Scalar dcb = dc0_ * (1 + (mH * mH)/KpHa_ + KpHb_/mH); //KpHb_ = 0!!!!!!        //[1/s]
         Scalar rdcb_ = dcb * porosity * Sw * cBio;         //[kg/m³s]

        return rdcb_;
    }
    Scalar rdcf(const Scalar densityBiofilm,
            const Scalar volFracBiofilm,
            const Scalar rprec,
            const Scalar densityCalcite,
            const Scalar volFracCalcite,
            const Scalar initialPorosity)
    {
        // compute biomass decay coefficient and rate:
        Scalar dcf = dc0_;
        dcf += rprec * FluidSystem::molarMass(CalciteIdx) /                 //[1/s]
             (densityCalcite * (initialPorosity - volFracCalcite));
        Scalar rdcf_ = dcf * densityBiofilm * volFracBiofilm; //[kg/m³s]

        return rdcf_;
    }


   void reactionSource(PrimaryVariables &q,
           const VolumeVariables &volVars,
           const Scalar absgradpw,
           const Scalar dt)
           {
//      //define and compute some parameters for siplicity:
     Scalar porosity = volVars.porosity();
     Scalar initialPorosity = volVars.initialPorosity();
     Scalar Sw  =  volVars.saturation(wPhaseIdx);
     Scalar xlSalinity = volVars.moleFracSalinity();
     Scalar densityBiofilm = volVars.density(bPhaseIdx);
     Scalar densityCalcite = volVars.density(cPhaseIdx);
     Scalar cBio = volVars.moleFraction(wPhaseIdx, BiosuspIdx) * volVars.molarDensity(wPhaseIdx) * FluidSystem::molarMass(BiosuspIdx);      //[kg_suspended_Biomass/m³_waterphase]
     if(cBio < 0)
         cBio = 0;
     Scalar volFracCalcite = volVars.precipitateVolumeFraction(cPhaseIdx);
     if (volFracCalcite < 0)
         volFracCalcite = 0;
     Scalar volFracBiofilm = volVars.precipitateVolumeFraction(bPhaseIdx);
     if (volFracBiofilm < 0)
         volFracBiofilm = 0;
     Scalar massBiofilm = densityBiofilm * volFracBiofilm;
     Scalar cSubstrate = volVars.moleFraction(wPhaseIdx, BiosubIdx) * volVars.molarDensity(wPhaseIdx) * FluidSystem::molarMass(BiosubIdx);  //[kg_substrate/m³_waterphase]
     if(cSubstrate < 0)
         cSubstrate = 0;
     Scalar cO2 = volVars.moleFraction(wPhaseIdx, O2Idx) * volVars.molarDensity(wPhaseIdx) * FluidSystem::molarMass(O2Idx);                 //[kg_oxygen/m³_waterphase]
     if(cO2 < 0)//1e-10)
         cO2 = 0;

     Scalar mH = moleFracToMolality(volVars.moleFraction(wPhaseIdx,HIdx), xlSalinity, volVars.moleFraction(wPhaseIdx,nCompIdx));  //[mol_H/kg_H2O]
     Scalar mNa = moleFracToMolality(volVars.moleFraction(wPhaseIdx,NaIdx), xlSalinity, volVars.moleFraction(wPhaseIdx,nCompIdx));  //[mol_sodium/kg_H2O]
     if (mNa < 0)
         mNa = 0;
     Scalar mCl = moleFracToMolality(volVars.moleFraction(wPhaseIdx,ClIdx), xlSalinity, volVars.moleFraction(wPhaseIdx,nCompIdx));  //[mol_chloride/kg_H2O]
     if (mCl < 0)
         mCl = 0;
     Scalar mUrea = moleFracToMolality(volVars.moleFraction(wPhaseIdx,UreaIdx), xlSalinity, volVars.moleFraction(wPhaseIdx,nCompIdx));  //[mol_urea/kg_H2O]
     if (mUrea < 0)
         mUrea = 0;
     Scalar mNH4 = moleFracToMolality(volVars.moleFraction(wPhaseIdx,NH4Idx), xlSalinity, volVars.moleFraction(wPhaseIdx,nCompIdx));  //[mol_NH4/kg_H2O]
     if (mNH4 < 0)
         mNH4 = 0;
     Scalar mCa = moleFracToMolality(volVars.moleFraction(wPhaseIdx,CaIdx), xlSalinity, volVars.moleFraction(wPhaseIdx,nCompIdx));  //[mol_calcium/kg_H2O]
     if (mCa < 0)
         mCa = 0;
     Scalar mCO3 = moleFracToMolality(volVars.moleFraction(wPhaseIdx,CO3Idx), xlSalinity, volVars.moleFraction(wPhaseIdx,nCompIdx));  //[mol_CO3/kg_H2O]
     if (mCO3 < 0)
         mCO3 = 0;
     Scalar mHCO3 = moleFracToMolality(volVars.moleFraction(wPhaseIdx,HCO3Idx), xlSalinity, volVars.moleFraction(wPhaseIdx,nCompIdx));  //[mol_HCO3/kg_H2O]
     if (mHCO3 < 0)
         mHCO3 = 0;
     Scalar temperature = volVars.temperature();

     // compute dissolution and precipitation rate of calcite
//     Scalar Ksp = Appa_Ksp( mNa,  mCa,  mNH4,  mHCO3,  mCO3,  mCl, volVars.temperature());
     Scalar Ksp = 3.31131e-9; //TODO test without calculated Ksp
     Scalar Omega = mCa * mCO3 / Ksp;

        Scalar Asw = Asw0_ * cbrt((1-volFracCalcite/initialPorosity)*(1-volFracCalcite/initialPorosity));   // TODO Asw should be a function of Sw, too!

     Scalar Acw = ac_ * volFracCalcite;
        if (ac_ * volFracCalcite > Asw)
            Acw = Asw;

     Scalar rdiss = 0;
     Scalar rprec = 0;
     if (Omega >= 1)
     {
         rdiss = 0;
         rprec = kprec_ * Asw * pow(Omega - 1 , nprec_);//[mol/dm³s]
         rprec *= 1000; // rprec [mol/m³s]
     }
     else
     {
          rdiss = (kdiss1_ * mH + kdiss2_) * Acw * pow((1 - Omega),ndiss_); //[mol/dm³s]
          rdiss *= 1000; // rdiss [mol/m³s]
          rprec = 0;
     }

     //compute biomass growth coefficient and rate
     Scalar mue = kmue_ * cSubstrate / (Ks_ + cSubstrate) * cO2 / (Ke_ + cO2);// [1/s]
     Scalar rgf = mue * massBiofilm;                //[kg/m³s]
     Scalar rgb = mue * porosity * Sw * cBio;   //[kg/m³s]

     if(cO2-(rgf+rgb)*dt<0)
     {
         mue =  mue * 0.99*cO2/((rgf+rgb)*dt);
         rgf = mue * massBiofilm;
         rgb = mue * porosity * Sw * cBio;
     }

     // compute biomass decay coefficient and rate:
     Scalar dcf = dc0_;
      dcf += rprec * FluidSystem::molarMass(CalciteIdx) /               //[1/s]
             (volVars.density(cPhaseIdx) * (initialPorosity - volFracCalcite));
     Scalar dcb = dc0_ * (1 + (mH * mH)/KpHa_ + KpHb_/mH); //KpHb_ = 0!!!!!!        //[1/s]
     Scalar rdcf = dcf * massBiofilm; //[kg/m³s]
     Scalar rdcb = dcb * porosity * Sw * cBio;      //[kg/m³s]

     // compute attachment coefficient and rate:
     Scalar ka = ca1_ * volFracBiofilm + ca2_;          //[1/s]
     Scalar ra = ka * porosity * Sw * cBio;             //[kg/m³s]

     // compute detachment coefficient and rate:
     Scalar cd2 = volFracBiofilm / (initialPorosity - volFracCalcite);      //[-]
     Scalar kd = cd1_ * pow((porosity * Sw * absgradpw),0.58) + cd2 * mue;  //[1/s]
     Scalar rd = kd * massBiofilm;                      //[kg/m³s]

     // compute rate of urealysis:
     //old rate with pH-dependence according to Fidaleo and Lavecchia
//   Scalar vmax = kurease_ / (1 + mH/Keu1_ +Keu2_/mH); //[molurea/(kgurease s)]

     Scalar vmax = kurease_; //According to new experimental results without pH dependence
     Scalar Zub = kub_ *  massBiofilm; //new nub_=1 ! pow(massBiofilm,nub_);        // [kgurease/m³]
     Scalar rurea = vmax * Zub * mUrea / ((Ku_ + mUrea) * (1 + mNH4 / KNH4_)); //[mol/m³s]

//     //check the reactions
//     std::stringstream  message;
//
//     // mass Check
//     const Scalar eps = plausibilityTolerance_ ;
//     const Scalar xTest = cO2-(rgf+rgb)*dt;
//
//     if (not std::isfinite(xTest) or xTest < 0.-eps or xTest > 1.+eps ){
//         message <<"\nOxygen would be consumed completely: \n";
//
//         message << "\t cO2 = " << cO2 <<"\n";
//         message << "\t cO2 consumed = " << (rgf+rgb)*dt <<"\n";
//     }
//
//     if (not std::isfinite(Omega) or Omega < 0.-eps or Omega > 1000.+eps ){
//          message <<"\n Omega, the calcite saturation index is out of a meaningful range: \n";
//
//          message << "\t Omega = " << Omega <<"\n";
//          message << "\t Asw = " << Asw <<"\n";
//          message << "\t mCa = " << mCa <<"\n";
//          message << "\t mCO3 = " << mCO3 <<"\n";
//          message << "\t rprec = " << rprec <<"\n";
//      }
//
//     Scalar maxRPrec= maxPrecipitateVolumePerTimestep_*volVars.density(cPhaseIdx)*FluidSystem::molarMass(CalciteIdx)/dt;
//
//     if (not std::isfinite(rprec) or rprec < 0.-eps or rprec > maxRPrec){
//          message <<"\n rprec is out of a meaningful range: \n";
//
//          message << "\t Omega = " << Omega <<"\n";
//          message << "\t Asw = " << Asw <<"\n";
//          message << "\t mCa = " << mCa <<"\n";
//          message << "\t mCO3 = " << mCO3 <<"\n";
//          message << "\t rprec = " << rprec <<"\n";
//      }
//
//     // Some check wrote into the error-message, add some additional information and throw
//     if (not message.str().empty()){
//
////         message << " all other mole fractions:" << "\n" ;
////         for(unsigned int compIdx=0; compIdx< numComponents+numSecComponents; ++ compIdx){
////             message << "moleFraction[" << compIdx << "]=" << variable[compIdx] << "\n";
//
//         DUNE_THROW(NumericalProblem, message.str());
//     }




     // rdiss+rprec[mol/m³s]
     // rurea[mol/m³s]
     // rgb + rdcb + ra + rd [kg/m³s]
     // q[kg/m³s]
     q[wCompIdx] += 0;
     q[nCompIdx] += rurea - rprec + rdiss;
     q[NaIdx] += 0;
     q[ClIdx] += 0;
     q[CaIdx] += - rprec + rdiss;
     q[UreaIdx] += - rurea;
     q[TNHIdx] += 2 * rurea;
     q[O2Idx] += -(rgf + rgb) *F_/Yield_ / FluidSystem::molarMass(O2Idx);
     q[BiosubIdx] += -(rgf + rgb) / Yield_ / FluidSystem::molarMass(BiosubIdx);
     q[BiosuspIdx] += (rgb - rdcb - ra + rd) / FluidSystem::molarMass(BiosuspIdx);
     q[phiBiofilmIdx] += (rgf - rdcf + ra - rd) / FluidSystem::molarMass(BiofilmIdx);
     q[phiCalciteIdx] += + rprec - rdiss;

}

private:

    //Newton Solver which returns true if convergence is reached and false if not.
    // x(i+1) = x(i) - f(i)/df(i) = x(i) + h(i)

    bool newton1D(Scalar &xVar, const Scalar tolAbs, const int maxIter)
    {
         /*NEWTON*/
        bool converge = false;
          Scalar eps = 1.e-3;
          Scalar eps2 = 1.e-10;
          Scalar b=0;
          Scalar c=100;
          Scalar r;
          Scalar pHc = - log(xVar);
          Scalar pHb = pHc+eps;
          Scalar Hb,Hc;
          Scalar CO3l,CO3r,CO3b, CO3c;
          Scalar NH3l,NH3r,NH3b, NH3c;
          Scalar error =100;
          iter_ = 0;
          int i = 0;
//        *HCO3 = *NH4 = CO3c = 0.;
          Scalar oh,hco3,nh4,co3,co2;
          oh=hco3=nh4=co3=co2=0;
          while (absolute(c) > tolAbs)
            {
              Hb = pow(10.,-pHb);
              CO3l = 0.; CO3r = cTot_;
              CO3b = (CO3l+CO3r)/2.;
              while (absolute(error)>1.E-11)
            {
              CO3r = CO3b + eps2;
              r = cTot_ - (Hb * CO3r / k2_)  - (Hb * (Hb*CO3r/k2_) / k1_) - CO3r;
              error = cTot_ - (Hb * CO3b / k2_)  - (Hb * (Hb*CO3b/k2_) / k1_) - CO3b;
              CO3b = CO3b - (eps2*error)/(r-error);
              i++;  if (i>1.E2) break;
            }

              hco3 = Hb * CO3b / k2_;
              co2 = Hb * hco3 / k1_;

              NH3l = 0.;
              NH3r = totalnh_;
              error =100.;
              i = 0;
              NH3b = (NH3l+NH3r)/2.;
              while (absolute(error)>1.E-11)
            {
              NH3r = NH3b + eps2;
              r = totalnh_ - Hb * NH3r / ka_ - NH3r;
              error = totalnh_ - Hb * NH3b / ka_ - NH3b;
              NH3b = NH3b - (eps2*error)/(r-error);
              i++;  if (i>1.E2) break;
            }
              nh4 = Hb * NH3b / ka_;

              oh = kw_ / Hb;
              b = - Hb + 2*CO3b + hco3 + oh - nh4 - na_ + cl_ - 2.*ca_;

              pHc = pHc - (eps*c)/(b-c);

              Hc = pow(10.,-pHc);
              CO3l = 0.;
              CO3r = cTot_;
              error =100.; i = 0;
              CO3c = (CO3l+CO3r)/2.;
              while (absolute(error)>1.E-11)
            {
              CO3r = CO3c + eps2;
              r = cTot_ - (Hc * CO3r / k2_)  - (Hc * (Hc*CO3r/k2_) / k1_) - CO3r;
              error = cTot_ - (Hc * CO3c / k2_)  - (Hc * (Hc*CO3c/k2_) / k1_) - CO3c;
              CO3c = CO3c - (eps2*error)/(r-error);
              i++; if (i>1.E2) break;
            }
              hco3 = Hc * CO3c / k2_;
              co2 = Hc * hco3 / k1_;

              NH3l = 0.;
              NH3r = totalnh_;
              error =100.;
              i = 0;
              NH3c = (NH3l+NH3r)/2.;
              while (absolute(error)>1.E-11)
            {
              NH3r = NH3c + eps2;
              r = totalnh_ - Hc * NH3r / ka_ - NH3r;
              error = totalnh_ - Hc * NH3c / ka_ - NH3c;
              NH3c = NH3c - (eps2*error)/(r-error);
              i++; if (i>1.E2) break;
            }
              nh4 = Hc * NH3c / ka_;

              oh = kw_ / Hc;
              c = - Hc + 2*CO3c + hco3 + oh - nh4 - na_ + cl_ - 2.*ca_;

              pHb = pHc+eps;
              iter_+=1;
              if (iter_>maxIter || isnan(error) || isnan(c))
            {
              /*sprintf(buf, "Bisection pH: %4.2f \n", pHc);
              UserWrite(buf);*/
              break;
            }
            }
          h_ = Hc;
          oh_ = kw_ / Hc;
          nh4_ = Hc * NH3c / ka_;
          co3_ = CO3c;
          hco3_ = Hc * CO3c / k2_;
          co2_ = Hc * hco3 / k1_;
//        (this->*funcPtr)(xVar);
//        Scalar h = -fdf_[0]/fdf_[1]; // h = x(i) - x(i-1)
//        Scalar hLast = h*0.5; //initial Step
//        iter_ = 0;
//        bool converge = false;
//        if (std::isnan(h))
//        {
//            return converge = false;
//        }
//
//        while(absolute(h) > tolAbs || absolute(h/hLast)  > 1 + tolRel)
//        {
//            if(iter_ > maxIter){break;}
//
//            if(iter_ > 0)
//            {
//                (this->*funcPtr)(xVar);
//                hLast = h;
//                h = -fdf_[0]/fdf_[1];
//            }
//            if (std::isnan(h))
//            {
//                return converge = false;
//            }
//
//            xVar = xVar + h;
//            iter_ = iter_ + 1;
//        }
        if(Hc < 0.0) {return converge = false;}
        if(iter_ <= maxIter) {converge = true;}
        return converge;

    }

    bool newton1D(Scalar &xVar, void (ThisType::*funcPtr)(Scalar), const Scalar tolAbs, const Scalar tolRel, const int maxIter)
    {
        if (!Valgrind::CheckDefined(xVar))
        {
            std::cout << "----!Valgrind::CheckDefined(xVar) in chemistry \n";
            DUNE_THROW(Dune::InvalidStateException, "xVar is not defined.");
        }
        (this->*funcPtr)(xVar);

        Scalar h = -fdf_[0]/fdf_[1]; // h = x(i) - x(i-1)
        Scalar hLast = h*0.5; //initial Step
        iter_ = 0;
        bool converge = false;
        if (std::isnan(h))
        {
            return converge = false;
        }

        while(absolute(h) > tolAbs || absolute(h/hLast)  > 1 + tolRel)
        {
            if(iter_ > maxIter){break;}

            if(iter_ > 0)
            {
                (this->*funcPtr)(xVar);
                hLast = h;
                h = -fdf_[0]/fdf_[1];
            }
            if (std::isnan(h))
            {
                return converge = false;
            }

            xVar = xVar + h;
            iter_ = iter_ + 1;
        }
        if(xVar < 0.0) {return converge = false;}
        if(iter_ <= maxIter) {converge = true; newtonOrBisection_ = true; }
        return converge;

    }

    //Bisection Method Solver returns true if convergence is reached and false if not.
    //xVar is the variable for which the system is solved
    //funcPtr is the pointer to the function which is to be solved
    //a0 is the lower starting value, b0 is the upper starting value. The root must be inside the interval [a0, b0]
    //tol is the stopping critium a-b
    bool bisection1D(Scalar &xVar, void (ThisType::*funcPtr)(Scalar), const Scalar a0, const Scalar b0, const Scalar tol)
    {
        Scalar iterNo = 0;
        int maxIter = 200;
        bool converge = false;
        int sfb, sfx;

        Scalar a = a0;
        Scalar b = b0;
        (this->*funcPtr)(b);
        sfb = sign(fdf_[0]);

        while(b-a > tol)
        {
            if(iterNo > maxIter)
            {
                return converge;
            }
            xVar = (b + a)/2;
            (this->*funcPtr)(xVar);
            sfx = sign(fdf_[0]);
            iterNo = iterNo + 1;
            if (sfx == 0)
                break;
            else
                {
                    if(sfx == sfb)
                    {
                        b = xVar;
                    }
                    else
                    {
                        a = xVar;
                    }
                }
        }
        newtonOrBisection_ = false;
        converge = true;
        return converge;
    }

    bool bisection1D(const Scalar tol)
    {
        bool converge = false;
      Scalar eps = 1.e-3;
      Scalar eps2 = 1.e-10;
        Scalar pHc = 7.;
        Scalar pHa = -1.;
        Scalar pHb = 15.;
        Scalar Ha,Hb,Hc;
        Scalar CO3r,CO3l,CO3a,CO3b,CO3c;
        Scalar NH3l,NH3r,NH3a,NH3b,NH3c;
        Scalar c=100.;
        Scalar a,b;
        Scalar error=100;
        Scalar r;
        iter_ = 0;
        int i = 0;
        Scalar oh,hco3,nh4,co3,co2;
        oh=hco3=nh4=co3=co2=0;
        while (absolute(c) > tol)
    {
      Ha =pow(10.,-pHa);
      CO3l = 0.;
      CO3r = cTot_;
      error =100.;
      i = 0;
      CO3a = (CO3l+CO3r)/2.;
      while (absolute(error)>1.E-10)
        {
          CO3r = CO3a + eps2;
          r = cTot_ - (Ha * CO3r / k2_)  - (Ha * (Ha*CO3r/k2_) / k1_) - CO3r;
          error = cTot_ - (Ha * CO3a / k2_)  - (Ha * (Ha*CO3a/k2_) / k1_) - CO3a;
          CO3a = CO3a - (eps2*error)/(r-error);
          i++;  if (i>1.E2) break;
        }

      hco3 = Ha * CO3a / k2_;
      co2 = Ha * hco3 / k1_;

      NH3l = 0.;
      NH3r = totalnh_;
      error =100.;
      i=0;
      NH3a = (NH3l+NH3r)/2.;
      while (absolute(error)>1.E-10)
        {
          NH3r = NH3a + eps2;
          r = totalnh_ - Ha * NH3r / ka_ - NH3r;
          error = totalnh_ - Ha * NH3a / ka_ - NH3a;
          NH3a = NH3a - (eps2*error)/(r-error);
          i++;  if (i>1.E2) break;
        }
      nh4 = Ha * NH3a / ka_;

      oh = kw_ / Ha;
      a = - Ha + 2*CO3a + hco3 + oh - nh4 - na_ + cl_ - 2.*ca_;

      Hb = pow(10.,-pHb);
      CO3l = 0.;
      CO3r = cTot_;
      error =100.;
      i = 0;
      CO3b = (CO3l+CO3r)/2.;
      while (absolute(error)>1.E-11)
        {
          CO3r = CO3b + eps2;
          r = cTot_ - (Hb * CO3r / k2_)  - (Hb * (Hb*CO3r/k2_) / k1_) - CO3r;
          error = cTot_ - (Hb * CO3b / k2_)  - (Hb * (Hb*CO3b/k2_) / k1_) - CO3b;
          CO3b = CO3b - (eps2*error)/(r-error);
          i++;  if (i>1.E2) break;
        }

      hco3 = Hb * CO3b / k2_;
      co2 = Hb * hco3 / k1_;

      NH3l = 0.;
      NH3r = totalnh_;
      error =100.;
      i = 0;
      NH3b = (NH3l+NH3r)/2.;
      while (absolute(error)>1.E-11)
        {
          NH3r = NH3b + eps2;
          r = totalnh_ - Hb * NH3r / ka_ - NH3r;
          error = totalnh_ - Hb * NH3b / ka_ - NH3b;
          NH3b = NH3b - (eps2*error)/(r-error);
          i++;  if (i>1.E2) break;
        }
      nh4 = Hb * NH3b / ka_;

      oh = kw_ / Hb;
      b = - Hb + 2*CO3b + hco3 + oh - nh4 - na_ + cl_ - 2.*ca_;

      pHc = (pHa + pHb)/2.;

      Hc = pow(10.,-pHc);
      CO3l = 0.;
      CO3r = cTot_;
      error =100.;
      i = 0;
      CO3c = (CO3l+CO3r)/2.;
      while (absolute(error)>1.E-10)
        {
          CO3r = CO3c + eps2;
          r = cTot_ - (Hc * CO3r / k2_)  - (Hc * (Hc*CO3r/k2_) / k1_) - CO3r;
          error = cTot_ - (Hc * CO3c / k2_)  - (Hc * (Hc*CO3c/k2_) / k1_) - CO3c;
          CO3c = CO3c - (eps2*error)/(r-error);
          i++; if (i>1.E2) break;
        }

      hco3 = Hc * CO3c / k2_;
      co2 = Hc * hco3 / k1_;

        NH3l = 0.;
        NH3r = totalnh_;
        error =100.;
        i = 0;
        NH3c = (NH3l+NH3r)/2.;
        while (absolute(error)>1.E-11)
    {
      NH3r = NH3c + eps2;
      r = totalnh_ - Hc * NH3r / ka_ - NH3r;
      error = totalnh_ - Hc * NH3c / ka_ - NH3c;
      NH3c = NH3c - (eps2*error)/(r-error);
      i++; if (i>1.E2) break;
    }
      nh4 = Hc * NH3c / ka_;

      oh = kw_ / Hc;
      c = - Hc + 2*CO3c + hco3 + oh - nh4 - na_ + cl_ - 2.*ca_;

      if (a*c<0.) pHb = pHc;
      else pHa = pHc;
      iter_+=1;

    }

      h_ = Hc;
      oh_ = kw_ / Hc;
      nh4_ = Hc * NH3c / ka_;
      co3_ = CO3c;
      hco3_ = Hc * CO3c / k2_;
      co2_ = Hc * hco3 / k1_;

//        Scalar iterNo = 0;
//        int maxIter = 100;
//        bool converge = false;
//        int sfb, sfx;
//
//        Scalar a = a0;
//        Scalar b = b0;
//        (this->*funcPtr)(b);
//        sfb = sign(fdf_[0]);
//
//        while(b-a > tol)
//        {
//            if(iterNo > maxIter)
//            {
//                return converge;
//            }
//            xVar = (b + a)/2;
//            (this->*funcPtr)(xVar);
//            sfx = sign(fdf_[0]);
//            iterNo = iterNo + 1;
//            if (sfx == 0)
//                break;
//            else
//                {
//                    if(sfx == sfb)
//                    {
//                        b = xVar;
//                    }
//                    else
//                    {
//                        a = xVar;
//                    }
//                }
//        }


                converge = true;
        return converge;
    }

//    void quadPoly(Scalar a, Scalar b, Scalar c)
//    {
//        x_ = (-b + sqrt(pow(b, 2) - 4*a*c))/2/a;
//        y_ = (-b - sqrt(pow(b, 2) - 4*a*c))/2/a;
//    }

    //Function solves electro neutrality equation f and derivative df/dH for H with constant CO2
    void H_CO2(Scalar activityH)
    {

        h_ = activityH;
        oh_ = kw_/h_;
        hco3_ = k1_*co2_/h_;
//         co3_ = k1_*k2_*co2_/pow(h_, 2.);
        co3_ = k1_*k2_*co2_/(h_*h_);
        nh4_ = totalnh_/(1+ka_/h_);
//        cTot_ = co2_ + hco3_ + co3_;
//        Scalar k1 = const1(pressure_, temperature_);
//        Scalar k2 = const2(pressure_, temperature_);
//        Scalar kw = constW(pressure_, temperature_);
//        Scalar ka = consta(pressure_, temperature_);
//        h_ = activityH/gammaH_;
//        Scalar activityCO2 = co2_*gammaCO2_;
//        Scalar activityNH3 =gammaNH3_ * gammaNH4_ * ka * totalnh_/(gammaNH4_ * ka + gammaNH3_ * activityH);
//        oh_ = kw/activityH/gammaOH_;
//        hco3_ = k1*activityCO2/activityH/gammaHCO3_;
//        co3_ = k1*k2*activityCO2/pow(activityH, 2.)/gammaCO3_;
//        nh4_ = activityNH3*activityH/gammaNH4_/ka;


        //Solve the function
//        Scalar f = h_ + 2*ca_ - oh_ - hco3_ - 2*co3_ ;
        Scalar f = h_ + 2*ca_ - oh_ - hco3_ - 2*co3_ + nh4_ + na_ - cl_;

        //solve the derivative analytically df/d(activityH)
//        Scalar df = 1/gammaH_ + kw/pow(activityH, 2.)/gammaOH_
//                + k1*activityCO2/pow(activityH, 2.)/gammaHCO3_
//                + 4*k1*k2*activityCO2/pow(activityH, 3.)/gammaCO3_;
//        Scalar df = 1/gammaH_ + kw/pow(activityH, 2.)/gammaOH_
//                + k1*activityCO2/pow(activityH, 2.)/gammaHCO3_
//                + 4*k1*k2*activityCO2/pow(activityH, 3.)/gammaCO3_
//                + ka*totalnh_*gammaNH3_ *gammaNH4_ / (pow(activityH * gammaNH3_ + ka * gammaNH4_, 2.));
//        Scalar df = 1 + kw_/pow(h_, 2.)               // H, OH
//              + co2_*k1_*(pow(h_, 2.))                //HCO3
//              + 4*co2_*k1_*k2_/pow(h_, 3.)            //CO3
//              + totalnh_*ka_/((h_+ka_)*(h_+ka_));     //NH4
//        Scalar df = 1 + kw_/(h_*h_) + co2_*k1_*(h_*h_)+ 4*co2_*k1_*k2_/(h_*h_*h_)  + totalnh_*ka_/((h_+ka_)*(h_+ka_));


        Scalar eps = 1e-8;
        Scalar xRight = h_ + eps*h_; // x + dx
        Scalar xLeft = h_ - eps*h_; // x - dx
        Scalar fRight = na_ + xRight + 2*ca_ - kw_/xRight - k1_*co2_/xRight - 2*k1_*k2_*co2_/(xRight*xRight) - cl_ + totalnh_/(1+ka_/xRight); // f(x+dx)
        Scalar fLeft = na_ + xLeft + 2*ca_ - kw_/xLeft -  k1_*co2_/xLeft - 2*k1_*k2_*co2_/(xLeft*xLeft) - cl_ + totalnh_/(1+ka_/xLeft); //  f(x-dx)
        Scalar df = (fRight - fLeft)/2/eps/h_; // {f(x+dx) - f(x-dx)}/2dx


        fdf_[0] = f;
        fdf_[1] = df;
     }


    void H_Ctot(Scalar activityH)
        {

        h_ = activityH;
        oh_ = kw_/h_;
        hco3_ = cTot_/(h_/k1_ + 1 + k2_/h_);
        co3_ = cTot_/((h_*h_)/k1_/k2_ + h_/k2_ + 1);
        co2_ = cTot_-co3_-hco3_;//h_*hco3_/k1_;
        nh4_ = totalnh_/(1+ka_/h_);
//        std::cout <<"cTot_ in H_CTot: "<< cTot_ <<"\n";
//        std::cout <<"totalnh_ in H_CTot: "<< totalnh_ <<"\n";
//        std::cout <<"h_ in H_CTot: "<< h_ <<"\n";
//        std::cout <<"oh_ in H_CTot: "<< oh_ <<"\n";
//        std::cout <<"nh4_ in H_CTot: "<< nh4_ <<"\n";
//        std::cout <<"co3_ in H_CTot: "<< co3_ <<"\n";
//        std::cout <<"hco3_ in H_CTot: "<< hco3_ <<"\n";
//        std::cout <<"co2_ in H_CTot: "<< co2_ <<"\n";

        //Solve the function
        Scalar f = na_ + h_ + 2*ca_ - oh_ - hco3_ - 2*co3_ - cl_ + nh4_;
        //Solve the derivative df/d(activityH)
//        Scalar df = 1 + kw_/pow(h_, 2)
//              + cTot_*k1_*(pow(h_, 2.) + 4*k2_*h_ + k1_*k2_)/pow((pow(h_, 2.) + k1_*h_ + k1_*k2_), 2)
//              + totalnh_*ka_/((h_+ka_)*(h_+ka_));
//        Scalar df = 1 + kw_/(h_*h_)                                                                       // H, OH
////                + cTot_*k1_*((h_*h_) + 4*k2_*h_ + k1_*k2_)/(((h_*h_) + k1_*h_ + k1_*k2_)*((h_*h_) + k1_*h_ + k1_*k2_))
//              + cTot_*k1_*(h_*h_-k1_*k2_)/((h_*h_+h_*k1_+k1_*k2_)*(h_*h_+h_*k1_+k1_*k2_))                 //HCO3
//              + 2*cTot_*k1_*k2_*(2*h_+k1_)/((h_*h_+h_*k1_+k1_*k2_)*(h_*h_+h_*k1_+k1_*k2_))                //CO3
//                + totalnh_*ka_/((h_+ka_)*(h_+ka_));                                                           //NH4
//        Scalar df = equationNumDeri(activityH);



        Scalar eps = 1e-8;
        Scalar xRight = h_ + eps*h_; // x + dx
        Scalar xLeft = h_ - eps*h_; // x - dx
        Scalar fRight = na_ + xRight + 2*ca_ - kw_/xRight - cTot_/(xRight/k1_ + 1 + k2_/xRight) - 2*cTot_/((xRight*xRight)/k1_/k2_ + xRight/k2_ + 1) - cl_ + totalnh_/(1+ka_/xRight); // f(x+dx)
        Scalar fLeft = na_ + xLeft + 2*ca_ - kw_/xLeft - cTot_/(xLeft/k1_ + 1 + k2_/xLeft) - 2*cTot_/((xLeft*xLeft)/k1_/k2_ + xLeft/k2_ + 1) - cl_ + totalnh_/(1+ka_/xLeft); //  f(x-dx)
        Scalar df = (fRight - fLeft)/2/eps/h_; // {f(x+dx) - f(x-dx)}/2dx


        fdf_[0] = f;
        fdf_[1] = df;


//        Scalar k1 = const1(pressure_, temperature_);
//        Scalar k2 = const2(pressure_, temperature_);
//        Scalar kw = constW(pressure_, temperature_);
//        Scalar ka = consta(pressure_, temperature_);
//        h_ = activityH/gammaH_;
////        Scalar activityCO3 = gammaCO3_*cTot_/(gammaCO3_*activityH*activityH/k1/k2 + gammaCO3_*activityH/k2/gammaHCO3_+1);
////        Scalar activityHCO3 = gammaHCO3_*cTot_/(gammaHCO3_*activityH/k1 + 1 + gammaHCO3_*k2/gammaCO3_/activityH);
//        //Scalar activityHCO3 = cTot_/(gammaHCO3_*activityH/k1 + 1 + gammaHCO3_*k2/gammaCO3_/activityH);
//        Scalar activityNH3 =gammaNH3_ * gammaNH4_ * ka * totalnh_/(gammaNH4_ * ka + gammaNH3_ * activityH);
//        oh_ = kw/activityH/gammaOH_;
//        co3_ = cTot_/(gammaCO3_*activityH*activityH/k1/k2 + gammaCO3_*activityH/k2/gammaHCO3_+1);//activityCO3 / gammaCO3_;
//        hco3_ = cTot_/(gammaHCO3_*activityH/k1 + 1 + gammaHCO3_*k2/gammaCO3_/activityH);//activityHCO3/gammaHCO3_;
//        nh4_ = activityNH3*activityH/gammaNH4_/ka;
//
//        //Solve the function
//        Scalar f = h_ + 2*ca_ - oh_ - hco3_ - 2*co3_ + na_ - cl_ + nh4_;
//
//        //solve the derivative analytically
//        Scalar df = 1/gammaH_ + kw/pow(activityH, 2)/gammaOH_
//                + ka*totalnh_ *gammaNH3_ *gammaNH4_ / (pow(activityH * gammaNH3_ + ka * gammaNH4_, 2))
////                + ((activityH*activityH*gammaCO3_ + 4*activityH*k2*gammaHCO3_ + k1*k2) *gammaHCO3_*gammaCO3_*k1*cTot_)
////                /(pow((activityH*activityH*gammaCO3_*gammaHCO3_ + activityH*k1*gammaCO3_ + k1*k1*gammaHCO3_),2)) * 1/gammaH_;
//                +cTot_*(gammaHCO3_/k1 -gammaHCO3_*k2/(gammaCO3_*activityH*activityH))/((gammaHCO3_*activityH/k1 + 1 + gammaHCO3_*k2/gammaCO3_/activityH)*(gammaHCO3_*activityH/k1 + 1 + gammaHCO3_*k2/gammaCO3_/activityH))
//                +2*cTot_*(2*gammaCO3_*activityH/k1/k2 + gammaCO3_/k2/gammaHCO3_)/((gammaCO3_*activityH*activityH/k1/k2 + gammaCO3_*activityH/k2/gammaHCO3_+1)*(gammaCO3_*activityH*activityH/k1/k2 + gammaCO3_*activityH/k2/gammaHCO3_+1));
////        Scalar df = equationNumDeri(activityH);
//
//        fdf_[0] = f;
//        fdf_[1] = df;
        }

    //Value of numerical derivative at xVar
    /*static*/ Scalar equationNumDeri(Scalar xVar)
    {
        Scalar eps = 1e-8;
        Scalar xRight = xVar + eps*xVar; // x + dx
        Scalar xLeft = xVar - eps*xVar; // x - dx
        Scalar fRight = equationValue(xRight); // f(x+dx)
        Scalar fLeft = equationValue(xLeft); // f(x-dx)
        Scalar df = (fRight - fLeft)/2/eps/xVar; // {f(x+dx) - f(x-dx)}/2dx
        return df;
     }



    Scalar absolute(Scalar x)
    {
        if(x<0.0)
        {
            return x*(-1);
        }
        else return x;
    }

    Scalar sign(Scalar x)
    {
        if(x > 0.0)
        {
           return 1;
        }
        else if (x < 0.0)
        {
           return -1;
        }
        else
        {
            return 0.0;
        }
    }



    int iter_; //Number of iterations the Newton solver needs until convergence
    Scalar pressure_;
    Scalar temperature_;
    Scalar salinity_;
    Scalar h2o_;
    Scalar co2_;
    Scalar hco3_;
    Scalar co3_;
    Scalar oh_;
    Scalar h_;
    Scalar ca_;
    Scalar na_;
    Scalar cl_;
    Scalar totalnh_;
    Scalar nh4_;
    Scalar initH_;
    Scalar ionicStrength_;
    Scalar cTot_;
    Scalar gammaH_;
    Scalar gammaCO2_;
    Scalar gammaCa_;
    Scalar gammaOH_;
    Scalar gammaHCO3_;
    Scalar gammaCO3_;
    Scalar gammaNH3_;
    Scalar gammaNH4_;
    SolVector fdf_; //Solution vector for the newtons solver every equation f solved by the newton solver for an unknown x
    // has to store f(x) in fdf_[0] and df/dx in fdf[1]
    Vector molality_;
    Vector charge_;
    Scalar x_;
    Scalar y_;
    Scalar k1_;
    Scalar k2_;
    Scalar kw_;
    Scalar ka_;
    Scalar apparentk1_;
    Scalar apparentk2_;
    Scalar apparentka_;
    bool newtonOrBisection_;

    static constexpr Scalar KpHb_ = 0;//9.14e-8;//[mol/kgH2O] Kim et al. 2000 //Not implemented by Anozie!!

    // biomass parameters
        Scalar ca1_;
        Scalar ca2_;
        Scalar cd1_;
        Scalar dc0_;
        Scalar kmue_ ;
        Scalar F_;
        Scalar Ke_;
        Scalar KpHa_;
        Scalar Ks_;
        Scalar Yield_;

    // calcite parameters
        Scalar ac_;
        Scalar kdiss1_;
        Scalar kdiss2_;
        Scalar kprec_;
        Scalar ndiss_;
        Scalar nprec_;
        Scalar Asw0_;

    // urease parameters
        Scalar kub_;
        Scalar kurease_;
//         Scalar nub_;
//         Scalar Keu1_;
//         Scalar Keu2_;
        Scalar KNH4_;
        Scalar Ku_;
        Scalar plausibilityTolerance_;
//        Scalar maxPrecipitateVolumePerTimestep_;

public:

    // biomass parameters
        Scalar ca1()    {       return ca1_; }
        Scalar ca2()    {       return ca2_; }
        Scalar cd1()    {       return cd1_; }
        Scalar dc0()    {       return dc0_; }
        Scalar kmue()    {      return kmue_; }
        Scalar F()    {         return F_; }
        Scalar Ke()    {        return Ke_; }
        Scalar KpHa()    {      return KpHa_; }
        Scalar Ks()    {        return Ks_; }
        Scalar Yield()    {     return Yield_; }

    // calcite parameters
        Scalar ac()    {        return ac_; }
        Scalar kdiss1()    {    return kdiss1_; }
        Scalar kdiss2()    {    return kdiss2_; }
        Scalar kprec()    {     return kprec_; }
        Scalar ndiss()    {     return ndiss_; }
        Scalar nprec()    {     return nprec_; }
        Scalar Asw0()    {      return Asw0_; }

    // urease parameters
        Scalar kub()    {       return kub_; }
        Scalar kurease()    {   return kurease_; }
//         Scalar nub()    {       return nub_; }
//         Scalar Keu1()    {      return Keu1_; }
//         Scalar Keu2()    {      return Keu2_; }
        Scalar KNH4()    {      return KNH4_; }
        Scalar Ku()    {        return Ku_; }

public:
    Scalar kprec() const
    {   return kprec_;}
    Scalar kub() const
    {   return kub_;}
    Scalar kurease() const
    {   return kurease_;}
    Scalar nprec() const
    {   return nprec_;}
    Scalar Asw0() const
    {   return Asw0_;}
//     Scalar Keu1() const
//     {   return Keu1_;}
//     Scalar Keu2() const
//     {   return Keu2_;}
    Scalar KNH4() const
    {   return KNH4_;}
    Scalar Ku() const
    {   return Ku_;}

    /*!
     * \brief Returns the mole fraction of NaCl \f$\mathrm{[mol \ NaCl / mol \ solution]}\f$  for a given mole fraction
     *
     * \param salinity the salinity \f$\mathrm{[kg \ NaCl / kg \ solution]}\f$
     */
    static Scalar salinityToMolFrac_(Scalar salinity) {

        const Scalar Mw = H2O::molarMass(); /* molecular weight of water [kg/mol] */
        const Scalar Ms = 58.8e-3; /* molecular weight of NaCl  [kg/mol] */

        const Scalar X_NaCl = salinity;
        /* salinity: conversion from mass fraction to mol fraction */
        const Scalar x_NaCl = -Mw * X_NaCl / ((Ms - Mw) * X_NaCl - Ms);
        return x_NaCl;
    }
};

} // end namespace

#endif
