#include <gtest/gtest.h>
#include <hqt/hello.hpp>

TEST(HelloTest, ReturnsVersionString) {
    EXPECT_EQ(hqt::hello(), "HQT Engine v0.1.0");
}

TEST(HelloTest, VersionStruct) {
    auto v = hqt::version();
    EXPECT_EQ(v.major, 0);
    EXPECT_EQ(v.minor, 1);
    EXPECT_EQ(v.patch, 0);
}
