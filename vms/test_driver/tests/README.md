This directory contains test-drivers that pretend to test the dummies, but actually test the `test_driver.rs` implementation. However, because they cosplay as "implementation tests", they get automatically executed alongside all other test drivers.

I'm sorry that this is so confusing. If you have a better explanation, please open a pull request.

For more info on test-drivers, see [0003_test_driver.md](../../../data-layout/0003_test_driver.md).
