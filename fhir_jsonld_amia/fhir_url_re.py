import re

# The following can be found in ./publish/references.html
# TODO: Need to make some sort of autoloader for this
R5_FHIR_URI_RE = re.compile(r'((http|https):\/\/([A-Za-z0-9\-\\\.\:\%\$]*\/)+)?(Account|ActivityDefinition|' \
                 r'AdministrableProductDefinition|AdverseEvent|AllergyIntolerance|Appointment|AppointmentResponse|' \
                 r'AuditEvent|Basic|Binary|BiologicallyDerivedProduct|BodyStructure|Bundle|CapabilityStatement|' \
                 r'CapabilityStatement2|CarePlan|CareTeam|CatalogEntry|ChargeItem|ChargeItemDefinition|Claim|' \
                 r'ClaimResponse|ClinicalImpression|ClinicalUseIssue|CodeSystem|Communication|CommunicationRequest|' \
                 r'CompartmentDefinition|Composition|ConceptMap|Condition|ConditionDefinition|Consent|Contract|' \
                 r'Coverage|CoverageEligibilityRequest|CoverageEligibilityResponse|DetectedIssue|Device|' \
                 r'DeviceDefinition|DeviceMetric|DeviceRequest|DeviceUseStatement|DiagnosticReport|DocumentManifest|' \
                 r'DocumentReference|EightBall|Encounter|Endpoint|EnrollmentRequest|EnrollmentResponse|EpisodeOfCare|' \
                 r'EventDefinition|Evidence|EvidenceVariable|ExampleScenario|ExplanationOfBenefit|' \
                 r'FamilyMemberHistory|Flag|Goal|GraphDefinition|Group|GuidanceResponse|HealthcareService|' \
                 r'ImagingStudy|Immunization|ImmunizationEvaluation|ImmunizationRecommendation|ImplementationGuide|' \
                 r'Ingredient|InsurancePlan|Invoice|Library|Linkage|List|Location|ManufacturedItemDefinition|' \
                 r'Measure|MeasureReport|Medication|MedicationAdministration|MedicationDispense|' \
                 r'MedicationKnowledge|MedicationRequest|MedicationUsage|MedicinalProductDefinition|' \
                 r'MessageDefinition|MessageHeader|MolecularSequence|NamingSystem|NutritionIntake|NutritionOrder|' \
                 r'NutritionProduct|Observation|ObservationDefinition|OperationDefinition|OperationOutcome|' \
                 r'Organization|OrganizationAffiliation|PackagedProductDefinition|Patient|PaymentNotice|' \
                 r'PaymentReconciliation|Permission|Person|PlanDefinition|Practitioner|PractitionerRole|Procedure|' \
                 r'Provenance|Questionnaire|QuestionnaireResponse|RegulatedAuthorization|RelatedPerson|RequestGroup|' \
                 r'ResearchStudy|ResearchSubject|RiskAssessment|Schedule|SearchParameter|ServiceRequest|Slot|' \
                 r'Specimen|SpecimenDefinition|StructureDefinition|StructureMap|Subscription|Substance|' \
                 r'SubstanceDefinition|SubstanceNucleicAcid|SubstancePolymer|SubstanceProtein|' \
                 r'SubstanceReferenceInformation|SubstanceSourceMaterial|SupplyDelivery|SupplyRequest|Task|' \
                 r'TerminologyCapabilities|TestReport|TestScript|Topic|ValueSet|VerificationResult|' \
                 r'VisionPrescription)\/[A-Za-z0-9\-\.]{1,64}(\/_history\/[A-Za-z0-9\-\.]{1,64})?$')
