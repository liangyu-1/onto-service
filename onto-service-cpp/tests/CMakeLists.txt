cmake_minimum_required(VERSION 3.16)

find_package(GTest REQUIRED)

set(TEST_SOURCES
    test_ontology_catalog.cc
    test_query_translator.cc
)

add_executable(onto_service_tests ${TEST_SOURCES})

target_link_libraries(onto_service_tests
    onto_service_cpp
    GTest::gtest_main
)

include(GoogleTest)
gtest_discover_tests(onto_service_tests)
