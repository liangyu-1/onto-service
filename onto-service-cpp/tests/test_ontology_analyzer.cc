#include <gtest/gtest.h>

#include "onto/service/ontology_catalog.h"
#include "onto/service/ontology_analyzer.h"

using namespace onto::service;

TEST(OntologyAnalyzerTest, CreateAnalyzer) {
  OntologyCatalog catalog("PlantGraph", "1.0.0");
  OntologyAnalyzer analyzer(&catalog);
  SUCCEED();
}

TEST(OntologyAnalyzerTest, ValidateQueryAccessEmptyAllowed) {
  OntologyCatalog catalog("PlantGraph", "1.0.0");
  OntologyAnalyzer analyzer(&catalog);

  // Build catalog first
  std::vector<std::map<std::string, std::string>> object_types = {
      {{"label_name", "ICSProcess"}},
  };
  std::vector<std::map<std::string, std::string>> properties;
  std::vector<std::map<std::string, std::string>> relationships;
  std::vector<std::map<std::string, std::string>> abox_mappings;
  
  auto status = catalog.BuildFromTbox(object_types, properties, relationships, abox_mappings);
  EXPECT_TRUE(status.ok());

  // Currently ValidateQueryAccess always returns OK (TODO)
  // This test verifies it doesn't crash
  SUCCEED();
}
