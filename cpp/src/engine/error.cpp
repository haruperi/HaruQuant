/**
 * @file error.cpp
 * @brief Shared error taxonomy implementation.
 */

#include "util/error.hpp"

namespace hqt::util {
namespace {

ErrorInfo make_trade_error(
    int code,
    const char* name,
    const char* message,
    bool retryable = false) {
    ErrorInfo info;
    info.code = code;
    info.name = name;
    info.message = message;
    info.domain = "trade";
    info.retryable = retryable;
    return info;
}

}  // namespace

ErrorInfo error_from_retcode(const int code) {
    switch (code) {
        case 0:
            return make_trade_error(0, "OK", "The operation completed successfully");
        case 1:
            return make_trade_error(1, "SUCCESS", "Success");
        case 10004:
            return make_trade_error(10004, "TRADE_RETCODE_REQUOTE", "Requote", true);
        case 10006:
            return make_trade_error(10006, "TRADE_RETCODE_REJECT", "Request rejected", true);
        case 10007:
            return make_trade_error(10007, "TRADE_RETCODE_CANCEL", "Request canceled by trader");
        case 10008:
            return make_trade_error(10008, "TRADE_RETCODE_PLACED", "Order placed");
        case 10009:
            return make_trade_error(10009, "TRADE_RETCODE_DONE", "Request completed");
        case 10010:
            return make_trade_error(10010, "TRADE_RETCODE_DONE_PARTIAL", "Only part of the request was completed");
        case 10011:
            return make_trade_error(10011, "TRADE_RETCODE_ERROR", "Request processing error", true);
        case 10012:
            return make_trade_error(10012, "TRADE_RETCODE_TIMEOUT", "Request canceled by timeout", true);
        case 10013:
            return make_trade_error(10013, "TRADE_RETCODE_INVALID", "Invalid request");
        case 10014:
            return make_trade_error(10014, "TRADE_RETCODE_INVALID_VOLUME", "Invalid volume");
        case 10015:
            return make_trade_error(10015, "TRADE_RETCODE_INVALID_PRICE", "Invalid price");
        case 10016:
            return make_trade_error(10016, "TRADE_RETCODE_INVALID_STOPS", "Invalid stops");
        case 10017:
            return make_trade_error(10017, "TRADE_RETCODE_TRADE_DISABLED", "Trade is disabled");
        case 10018:
            return make_trade_error(10018, "TRADE_RETCODE_MARKET_CLOSED", "Market is closed", true);
        case 10019:
            return make_trade_error(
                10019,
                "TRADE_RETCODE_NO_MONEY",
                "There is not enough money to complete the request");
        case 10020:
            return make_trade_error(10020, "TRADE_RETCODE_PRICE_CHANGED", "Prices changed", true);
        case 10021:
            return make_trade_error(
                10021,
                "TRADE_RETCODE_PRICE_OFF",
                "There are no quotes to process the request",
                true);
        case 10022:
            return make_trade_error(10022, "TRADE_RETCODE_INVALID_EXPIRATION", "Invalid expiration");
        case 10023:
            return make_trade_error(10023, "TRADE_RETCODE_ORDER_CHANGED", "Order state changed", true);
        case 10024:
            return make_trade_error(10024, "TRADE_RETCODE_TOO_MANY_REQUESTS", "Too frequent requests", true);
        case 10025:
            return make_trade_error(10025, "TRADE_RETCODE_NO_CHANGES", "No changes in request");
        case 10026:
            return make_trade_error(10026, "TRADE_RETCODE_SERVER_DISABLES_AT", "Autotrading disabled by server");
        case 10027:
            return make_trade_error(10027, "TRADE_RETCODE_CLIENT_DISABLES_AT", "Autotrading disabled by client");
        case 10028:
            return make_trade_error(10028, "TRADE_RETCODE_LOCKED", "Request locked for processing", true);
        case 10029:
            return make_trade_error(10029, "TRADE_RETCODE_FROZEN", "Order or position frozen");
        case 10030:
            return make_trade_error(10030, "TRADE_RETCODE_INVALID_FILL", "Invalid order filling type");
        case 10031:
            return make_trade_error(
                10031,
                "TRADE_RETCODE_CONNECTION",
                "No connection with the trade server",
                true);
        case 10032:
            return make_trade_error(10032, "TRADE_RETCODE_ONLY_REAL", "Only long positions allowed");
        case 10033:
            return make_trade_error(10033, "TRADE_RETCODE_LIMIT_ORDERS", "Only short positions allowed");
        case 10034:
            return make_trade_error(10034, "TRADE_RETCODE_LIMIT_VOLUME", "Only closing positions allowed");
        case 10035:
            return make_trade_error(10035, "TRADE_RETCODE_INVALID_ORDER", "Position closed");
        case 10036:
            return make_trade_error(10036, "TRADE_RETCODE_POSITION_CLOSED", "Invalid close volume");
        default: {
            ErrorInfo info;
            info.code = code;
            info.name = "UNKNOWN";
            info.message = "Unknown error";
            info.domain = "trade";
            info.retryable = false;
            return info;
        }
    }
}

std::string error_name(const int code) {
    return error_from_retcode(code).name;
}

bool is_success_retcode(const int code) noexcept {
    return code == 0 || code == 1 || code == 10008 || code == 10009 || code == 10010;
}

}  // namespace hqt::util

