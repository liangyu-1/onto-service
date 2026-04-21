#include <gtest/gtest.h>

#include "onto/service/ontology_catalog.h"
#include "onto/service/query_translator.h"

using namespace onto::service;

TEST(QueryTranslatorTest, CreateTranslator) {
  OntologyCatalog catalog("PlantGraph", "1.0.0");
  QueryTranslator translator(&catalog);
  // Just verify it doesn't crash
  SUCCEED();
}

TEST(QueryTranslatorTest, TranslateNullAst) {
  OntologyCatalog catalog("PlantGraph", "1.0.0");
  QueryTranslator translator(&catalog);

  auto result = translator.TranslateToDorisSql(nullptr);
  EXPECT_FALSE(result.ok());
}
