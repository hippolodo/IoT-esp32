package com.iot.backend.util;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;

/** Parses date/time filters with day, hour, minute, or second precision. */
public final class TimeRangeParser {
    private TimeRangeParser() {
    }

    public static TimeRange parse(String startTime, String endTime) {
        boolean startMissing = startTime == null || startTime.isBlank();
        boolean endMissing = endTime == null || endTime.isBlank();

        if (startMissing && endMissing) {
            return new TimeRange(null, null);
        }
        if (startMissing || endMissing) {
            throw new IllegalArgumentException("startTime và endTime phải được nhập cùng nhau");
        }

        LocalDateTime start = parseStart(startTime.trim());
        LocalDateTime endExclusive = parseEndExclusive(endTime.trim());
        if (!start.isBefore(endExclusive)) {
            throw new IllegalArgumentException("startTime phải nhỏ hơn hoặc bằng endTime");
        }
        return new TimeRange(start, endExclusive);
    }

    private static LocalDateTime parseStart(String value) {
        if (!value.matches("\\d{4}-\\d{2}-\\d{2}( \\d{2}(:\\d{2}(:\\d{2})?)?)?")) {
            throw new IllegalArgumentException("Thời gian phải theo yyyy-MM-dd, yyyy-MM-dd HH, yyyy-MM-dd HH:mm hoặc yyyy-MM-dd HH:mm:ss");
        }
        try {
            return switch (value.length()) {
                case 10 -> LocalDate.parse(value, DateTimeFormatter.ISO_LOCAL_DATE).atStartOfDay();
                case 13 -> LocalDate.parse(value.substring(0, 10), DateTimeFormatter.ISO_LOCAL_DATE)
                        .atTime(Integer.parseInt(value.substring(11, 13)), 0);
                case 16 -> LocalDate.parse(value.substring(0, 10), DateTimeFormatter.ISO_LOCAL_DATE)
                        .atTime(Integer.parseInt(value.substring(11, 13)), Integer.parseInt(value.substring(14, 16)));
                case 19 -> LocalDateTime.parse(value, DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
                default -> throw new IllegalArgumentException("Thời gian phải theo yyyy-MM-dd, yyyy-MM-dd HH, yyyy-MM-dd HH:mm hoặc yyyy-MM-dd HH:mm:ss");
            };
        } catch (DateTimeParseException exception) {
            throw new IllegalArgumentException("Định dạng thời gian không hợp lệ", exception);
        }
    }

    private static LocalDateTime parseEndExclusive(String value) {
        LocalDateTime parsed = parseStart(value);
        return switch (value.length()) {
            case 10 -> parsed.plusDays(1);
            case 13 -> parsed.plusHours(1);
            case 16 -> parsed.plusMinutes(1);
            case 19 -> parsed.plusSeconds(1);
            default -> throw new IllegalArgumentException("Định dạng thời gian không hợp lệ");
        };
    }

    public record TimeRange(LocalDateTime start, LocalDateTime endExclusive) {
    }
}
