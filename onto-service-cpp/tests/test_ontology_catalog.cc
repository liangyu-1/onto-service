#include <gtest/gtest.h>

#include "onto/service/ontology_catalog.h"

using namespace onto::service;

TEST(OntologyCatalogTest, CreateCatalog) {
  OntologyCatalog catalog("PlantGraph", "1.0.0");
  EXPECT_NE(catalog.GetCatalog(), nullptr);
}

TEST(OntologyCatalogTest, BuildFromTbox) {
  OntologyCatalog catalog("PlantGraph", "1.0.0");

  std::vector<std::map<std::string, std::string>> object_types = {
      {{"label_name", "ICSProcess"}, {"parent_label", ""}, {"display_name", "工艺过程"}},
      {{"label_name", "SCADAPoint"}, {"parent_label", ""}, {"display_name", "SCADA点位"}},
  };

  std::vector<std::map<std::string, std::string>> properties = {
      {{"owner_label", "ICSProcess"}, {"property_name", "process_id"}, {"value_type", "STRING"}},
      {{"owner_label", "ICSProcess"}, {"property_name", "security_state"}, {"value_type", "STRING"}},
      {{"owner_label", "SCADAPoint"}, {"property_name", "point_tag"}, {"value_type", "STRING"}},
      {{"owner_label", "SCADAPoint"}, {"property_name", "latest_value"}, {"value_type", "DOUBLE"}},
  };

  std::vector<std::map<std::string, std::string>> relationships = {
      {{"label_name", "HAS_POINT"}, {"source_label", "ICSProcess"}, {"target_label", "SCADAPoint"}},
  };

  std::vector<std::map<std::string, std::string>> abox_mappings = {
      {{"class_name", "ICSProcess"}, {"object_source_name", "dim_process"}, {"primary_key", "process_id"}},
      {{"class_name", "SCADAPoint"}, {"object_source_name", "dim_point"}, {"primary_key", "point_tag"}},
  };

  auto status = catalog.BuildFromTbox(object_types, properties, relationships, abox_mappings);
  EXPECT_TRUE(status.ok()) << status.ToString();

  auto* graph = catalog.GetPropertyGraph();
  EXPECT_NE(graph, nullptr);
}

TEST(OntologyCatalogTest, RefreshCatalog) {
  OntologyCatalog catalog("PlantGraph", "1.0.0");
  auto status = catalog.Refresh();
  EXPECT_TRUE(status.ok());
}
