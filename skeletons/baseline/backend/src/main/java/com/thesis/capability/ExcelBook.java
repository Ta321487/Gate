package com.thesis.capability;

import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.DataFormatter;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.SheetVisibility;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * xlsx 读写（Apache POI）。导入表用中文表头；字段键放在隐藏表，避免中文列对不上。
 */
public final class ExcelBook {

    public static final String IMPORT_SHEET = "导入";
    static final String KEY_SHEET = "_keys";
    static final int MAX_ROWS = 5000;

    private ExcelBook() {}

    public static byte[] template(List<String> labels, List<String> keys, List<String> samples) throws IOException {
        try (XSSFWorkbook wb = new XSSFWorkbook()) {
            Sheet sheet = wb.createSheet(IMPORT_SHEET);
            writeRow(sheet, 0, labels);
            Sheet note = wb.createSheet("填写说明");
            writeRow(note, 0, List.of("请在「导入」表从第 2 行填写。下面是各列示例，不要把本表拿去导入。"));
            writeRow(note, 1, labels);
            if (samples != null && !samples.isEmpty()) {
                writeRow(note, 2, samples);
            }
            Sheet keysSheet = wb.createSheet(KEY_SHEET);
            writeRow(keysSheet, 0, keys);
            wb.setSheetVisibility(wb.getSheetIndex(keysSheet), SheetVisibility.VERY_HIDDEN);
            sheet.createFreezePane(0, 1);
            for (int i = 0; i < labels.size(); i++) {
                sheet.setColumnWidth(i, 18 * 256);
            }
            return bytes(wb);
        }
    }

    public static byte[] table(String sheetName, List<String> labels, List<List<String>> rows) throws IOException {
        try (XSSFWorkbook wb = new XSSFWorkbook()) {
            Sheet sheet = wb.createSheet(sheetName == null || sheetName.isBlank() ? "导出" : sheetName);
            writeRow(sheet, 0, labels);
            if (rows != null) {
                int r = 1;
                for (List<String> row : rows) {
                    if (r > MAX_ROWS) break;
                    writeRow(sheet, r, row);
                    r++;
                }
            }
            sheet.createFreezePane(0, 1);
            return bytes(wb);
        }
    }

    /** 读导入簿。优先用隐藏表里的字段键；没有则用表头原文。 */
    public static List<Map<String, String>> readImport(InputStream in) throws IOException {
        try (XSSFWorkbook wb = new XSSFWorkbook(in)) {
            Sheet sheet = wb.getSheet(IMPORT_SHEET);
            if (sheet == null) sheet = wb.getNumberOfSheets() > 0 ? wb.getSheetAt(0) : null;
            if (sheet == null) return List.of();
            DataFormatter fmt = new DataFormatter();
            List<String> keys = readKeyRow(wb, fmt);
            Row head = sheet.getRow(0);
            int width = head == null ? 0 : head.getLastCellNum();
            if (keys.isEmpty()) {
                keys = readCells(head, width, fmt);
            }
            if (width < keys.size()) width = keys.size();
            List<Map<String, String>> rows = new ArrayList<>();
            int last = sheet.getLastRowNum();
            for (int i = 1; i <= last; i++) {
                if (rows.size() >= MAX_ROWS) break;
                Row row = sheet.getRow(i);
                List<String> cells = readCells(row, width, fmt);
                if (isBlank(cells)) continue;
                Map<String, String> map = new LinkedHashMap<>();
                for (int c = 0; c < keys.size() && c < cells.size(); c++) {
                    String key = keys.get(c) == null ? "" : keys.get(c).trim();
                    if (key.isEmpty()) continue;
                    map.put(key, cells.get(c) == null ? "" : cells.get(c).trim());
                }
                map.put("__line", String.valueOf(i + 1));
                rows.add(map);
            }
            return rows;
        }
    }

    private static List<String> readKeyRow(XSSFWorkbook wb, DataFormatter fmt) {
        Sheet keys = wb.getSheet(KEY_SHEET);
        if (keys == null) return List.of();
        Row row = keys.getRow(0);
        if (row == null) return List.of();
        return readCells(row, row.getLastCellNum(), fmt);
    }

    private static List<String> readCells(Row row, int width, DataFormatter fmt) {
        List<String> cells = new ArrayList<>();
        if (width < 0) width = 0;
        for (int c = 0; c < width; c++) {
            if (row == null) {
                cells.add("");
                continue;
            }
            Cell cell = row.getCell(c);
            cells.add(cell == null ? "" : fmt.formatCellValue(cell));
        }
        return cells;
    }

    private static boolean isBlank(List<String> cells) {
        for (String c : cells) {
            if (c != null && !c.isBlank()) return false;
        }
        return true;
    }

    private static void writeRow(Sheet sheet, int index, List<String> values) {
        Row row = sheet.createRow(index);
        if (values == null) return;
        for (int i = 0; i < values.size(); i++) {
            Cell cell = row.createCell(i);
            cell.setCellValue(values.get(i) == null ? "" : values.get(i));
        }
    }

    private static byte[] bytes(XSSFWorkbook wb) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        wb.write(out);
        return out.toByteArray();
    }
}
