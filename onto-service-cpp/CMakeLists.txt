cmake_minimum_required(VERSION 3.16)
project(onto_service_cpp VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find GoogleSQL (ZetaSQL)
set(GOOGLESQL_ROOT ${CMAKE_CURRENT_SOURCE_DIR}/../googlesql)

# Include directories
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${GOOGLESQL_ROOT}
    ${GOOGLESQL_ROOT}/googlesql/public
    ${GOOGLESQL_ROOT}/googlesql/base
)

# Source files
set(SOURCES
    src/ontology_catalog.cc
    src/ontology_analyzer.cc
    src/query_translator.cc
)

# Header files
set(HEADERS
    include/onto/service/ontology_catalog.h
    include/onto/service/ontology_analyzer.h
    include/onto/service/query_translator.h
)

# Library
add_library(onto_service_cpp STATIC ${SOURCES} ${HEADERS})

# Link with GoogleSQL (if available)
# target_link_libraries(onto_service_cpp googlesql)

# Tests
enable_testing()
add_subdirectory(tests)
