#include <gtest/gtest.h>

#include "onto/service/ontology_catalog.h"
#include "onto/service/query_translator.h"

using namespace onto::service;

TEST(QueryTranslatorTest, CreateTranslator) {
  OntologyCatalog catalog("PlantGraph", "1.0.0");
  QueryTranslator translator(&catalog);
  SUCCEED();
}

TEST(QueryTranslatorTest, TranslateNullAst) {
  OntologyCatalog catalog("PlantGraph", "1.0.0");
  QueryTranslator translator(&catalog);

  auto result = translator.TranslateToDorisSql(nullptr);
  EXPECT_FALSE(result.ok());
}

TEST(QueryTranslatorTest, ResolvePropertyProjection) {
  OntologyCatalog catalog("PlantGraph", "1.0.0");
  QueryTranslator translator(&catalog);

  // Without actual DB mapping, should return the semantic property name
  auto result = translator.ResolvePropertyProjection("security_state", "ICSProcess");
  EXPECT_TRUE(result.ok());
  EXPECT_EQ(result.value(), "security_state");
}

TEST(QueryTranslatorTest, ResolveRelationshipNavigation) {
  OntologyCatalog catalog("PlantGraph", "1.0.0");
  QueryTranslator translator(&catalog);

  auto result = translator.ResolveRelationshipNavigation("ICSProcess", "has_point");
  EXPECT_TRUE(result.ok());
  EXPECT_NE(result.value().find("Navigation"), std::string::npos);
}

TEST(QueryTranslatorTest, GenerateSqlWithMvHint) {
  OntologyCatalog catalog("PlantGraph", "1.0.0");
  QueryTranslator translator(&catalog);

  auto result = translator.GenerateSqlWithMvHint(
      "SELECT * FROM dim_process",
      {"mv_process_state", "mv_process_metrics"});
  
  EXPECT_TRUE(result.ok());
  EXPECT_NE(result.value().find("mv_process_state"), std::string::npos);
}
