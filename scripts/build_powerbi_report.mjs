#!/usr/bin/env node

/**
 * Deterministically builds the K-APT AX Control Tower PBIR report layer.
 *
 * Run from the repository root:
 *   node scripts/build_powerbi_report.mjs
 *
 * The script replaces report pages only. The semantic model and source data
 * remain untouched. Page and visual IDs are stable across repeated runs.
 */

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "..");
const reportDir = path.join(
  repoRoot,
  "powerbi",
  "KAPT_AX_Control_Tower.Report",
);
const definitionDir = path.join(reportDir, "definition");
const pagesDir = path.join(definitionDir, "pages");

const VISUAL_SCHEMA =
  "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json";
const PAGE_SCHEMA =
  "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json";
const PAGES_SCHEMA =
  "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json";
const PBIR_SCHEMA =
  "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/1.0.0/schema.json";

const COLORS = {
  navy: "#142A43",
  navyLight: "#1F466C",
  orange: "#E67E22",
  blue: "#2F80ED",
  green: "#2E7D32",
  red: "#C0392B",
  yellow: "#F2C94C",
  purple: "#7B61A8",
  teal: "#00A6A6",
  text: "#1F2937",
  textSecondary: "#64748B",
  muted: "#8A94A6",
  border: "#D9E0E7",
  grid: "#E5E7EB",
  page: "#F4F6F8",
  white: "#FFFFFF",
  band: "#F8FAFC",
  headerText: "#D7E0EA",
  note: "#FFF7ED",
};

const FONT = "Segoe UI";

function stableHex(value, length = 20) {
  return crypto.createHash("sha1").update(value).digest("hex").slice(0, length);
}

function pageId(key) {
  return stableHex(`kapt-page:${key}`);
}

function visualId(pageKey, key) {
  return stableHex(`kapt-visual:${pageKey}:${key}`);
}

function filterId(pageKey, key) {
  return `Filter${stableHex(`kapt-filter:${pageKey}:${key}`, 24)}`;
}

function literal(value) {
  return { expr: { Literal: { Value: value } } };
}

function bool(value) {
  return literal(value ? "true" : "false");
}

function integer(value) {
  return literal(`${value}L`);
}

function number(value) {
  return literal(`${value}D`);
}

function text(value) {
  const escaped = String(value).replaceAll("'", "''");
  return literal(`'${escaped}'`);
}

function color(value) {
  return {
    solid: {
      color: text(value),
    },
  };
}

function column(table, property) {
  return {
    Column: {
      Expression: { SourceRef: { Entity: table } },
      Property: property,
    },
  };
}

function measure(table, property) {
  return {
    Measure: {
      Expression: { SourceRef: { Entity: table } },
      Property: property,
    },
  };
}

function aggregation(table, property, fn = 4) {
  return {
    Aggregation: {
      Expression: column(table, property),
      Function: fn,
    },
  };
}

const AGG_NAMES = {
  0: "Sum",
  1: "Avg",
  2: "Count",
  3: "Min",
  4: "Max",
  5: "CountNonNull",
  6: "Median",
  7: "StdDev",
  8: "Var",
};

function projection({
  table,
  property,
  kind = "column",
  fn = 4,
  displayName,
  active,
}) {
  let field;
  let queryRef;
  if (kind === "measure") {
    field = measure(table, property);
    queryRef = `${table}.${property}`;
  } else if (kind === "aggregation") {
    field = aggregation(table, property, fn);
    queryRef = `${AGG_NAMES[fn]}(${table}.${property})`;
  } else {
    field = column(table, property);
    queryRef = `${table}.${property}`;
  }

  const item = {
    field,
    queryRef,
    nativeQueryRef: displayName ?? property,
  };
  if (displayName) item.displayName = displayName;
  if (active !== undefined) item.active = active;
  return item;
}

function categoricalFilter(pageKey, key, table, property, value) {
  const alias = stableHex(`${pageKey}:${key}:alias`, 1);
  let encodedValue;
  if (typeof value === "boolean") encodedValue = value ? "true" : "false";
  else if (typeof value === "number") encodedValue = `${value}D`;
  else encodedValue = `'${String(value).replaceAll("'", "''")}'`;

  return {
    name: filterId(pageKey, key),
    field: column(table, property),
    type: "Categorical",
    filter: {
      Version: 2,
      From: [{ Name: alias, Entity: table, Type: 0 }],
      Where: [
        {
          Condition: {
            In: {
              Expressions: [
                {
                  Column: {
                    Expression: { SourceRef: { Source: alias } },
                    Property: property,
                  },
                },
              ],
              Values: [[{ Literal: { Value: encodedValue } }]],
            },
          },
        },
      ],
    },
    howCreated: "User",
  };
}

function pageObjects() {
  return {
    background: [
      {
        properties: {
          color: color(COLORS.page),
          transparency: number(0),
        },
      },
    ],
    outspace: [
      {
        properties: {
          color: color(COLORS.page),
          transparency: number(0),
        },
      },
    ],
  };
}

function containerObjects(titleValue, options = {}) {
  const {
    background = true,
    border = true,
    shadow = true,
    titleSize = 12,
  } = options;
  const result = {
    background: [
      {
        properties: {
          show: bool(background),
          color: color(COLORS.white),
          transparency: number(0),
        },
      },
    ],
    border: [
      {
        properties: {
          show: bool(border),
          color: color(COLORS.border),
          radius: number(8),
          width: number(1),
        },
      },
    ],
    dropShadow: [
      {
        properties: {
          show: bool(shadow),
          preset: text("BottomRight"),
          position: text("Outer"),
          color: color("#AAB4C0"),
          transparency: number(78),
          shadowSpread: number(0),
          shadowBlur: number(6),
          angle: number(45),
          shadowDistance: number(2),
        },
      },
    ],
    visualHeader: [
      {
        properties: {
          show: bool(false),
        },
      },
    ],
  };

  result.title = [
    {
      properties: {
        show: bool(Boolean(titleValue)),
        text: text(titleValue ?? ""),
        heading: text("Normal"),
        titleWrap: bool(true),
        fontColor: color(COLORS.navy),
        alignment: text("Left"),
        fontSize: number(titleSize),
        bold: bool(true),
        fontFamily: text(FONT),
      },
    },
  ];
  return result;
}

function visualShell(pageKey, key, type, position, visual, filters = []) {
  const name = visualId(pageKey, key);
  const shell = {
    $schema: VISUAL_SCHEMA,
    name,
    position: {
      x: position.x,
      y: position.y,
      z: position.z,
      height: position.height,
      width: position.width,
      tabOrder: position.tabOrder ?? position.z,
    },
    visual: {
      visualType: type,
      ...visual,
      drillFilterOtherVisuals: true,
    },
  };
  if (filters.length) shell.filterConfig = { filters };
  return shell;
}

function shapeVisual(pageKey, key, position, shapeType, fillColor) {
  return visualShell(pageKey, key, "shape", position, {
    objects: {
      shape: [
        {
          properties: {
            tileShape: text(shapeType),
          },
        },
      ],
      rotation: [
        {
          properties: {
            shapeAngle: integer(0),
          },
        },
      ],
      fill: [
        {
          properties: {
            show: bool(true),
            fillColor: color(fillColor),
            transparency: number(0),
          },
          selector: { id: "default" },
        },
      ],
      outline: [
        {
          properties: { show: bool(false) },
          selector: { id: "default" },
        },
      ],
    },
  });
}

function textboxVisual(pageKey, key, position, runs, options = {}) {
  const paragraphs = [
    {
      textRuns: runs.map((run) => ({
        value: run.value,
        textStyle: {
          fontFamily: run.fontFamily ?? FONT,
          fontWeight: run.bold ? "bold" : "normal",
          fontSize: `${run.size ?? 10}pt`,
          color: run.color ?? COLORS.text,
        },
      })),
    },
  ];
  const background = options.background ?? false;
  const border = options.border ?? false;
  const vco = containerObjects(null, {
    background,
    border,
    shadow: options.shadow ?? false,
  });
  if (background && options.backgroundColor) {
    vco.background[0].properties.color = color(options.backgroundColor);
  }
  if (border && options.borderColor) {
    vco.border[0].properties.color = color(options.borderColor);
  }
  return visualShell(pageKey, key, "textbox", position, {
    objects: { general: [{ properties: { paragraphs } }] },
    visualContainerObjects: vco,
  });
}

function cardVisual(pageKey, key, position, measureName, label, accent) {
  const p = projection({
    table: "_Measures",
    property: measureName,
    kind: "measure",
    displayName: label,
  });
  return visualShell(pageKey, key, "cardVisual", position, {
    query: { queryState: { Data: { projections: [p] } } },
    objects: {
      value: [
        {
          properties: {
            show: bool(true),
            fontFamily: text(FONT),
            fontSize: number(17),
            bold: bool(true),
            fontColor: color(accent),
            horizontalAlignment: text("left"),
            textWrap: bool(false),
            labelDisplayUnits: number(0),
            labelPrecision: integer(1),
            showBlankAs: text("0"),
          },
          selector: { id: "default" },
        },
      ],
      label: [
        {
          properties: {
            show: bool(true),
            text: text(label),
            fontFamily: text(FONT),
            fontSize: number(8),
            bold: bool(false),
            fontColor: color(COLORS.textSecondary),
            position: text("belowValue"),
            textWrap: bool(false),
            horizontalAlignment: text("left"),
          },
          selector: { id: "default" },
        },
      ],
      accentBar: [
        {
          properties: {
            show: bool(true),
            width: integer(4),
            color: color(accent),
            transparency: integer(0),
          },
          selector: { id: "default" },
        },
      ],
      shapeCustomRectangle: [
        {
          properties: {
            tileShape: text("rectangleRoundedByPixel"),
            rectangleRoundedCurve: integer(8),
          },
          selector: { id: "default" },
        },
      ],
      layout: [
        {
          properties: {
            customizePadding: bool(true),
            rowPadding: integer(0),
            columnPadding: integer(0),
            leftOuterMargin: integer(6),
            rightOuterMargin: integer(6),
            topOuterMargin: integer(2),
            bottomOuterMargin: integer(2),
          },
          selector: { id: "default" },
        },
      ],
      padding: [
        {
          properties: {
            paddingSelection: text("Custom"),
            paddingUniform: integer(4),
            paddingIndividual: bool(false),
          },
          selector: { id: "default" },
        },
      ],
      spacing: [
        {
          properties: { verticalSpacing: integer(0) },
          selector: { id: "default" },
        },
      ],
    },
    visualContainerObjects: containerObjects(null),
  });
}

function slicerVisual(pageKey, key, position, table, property, label) {
  const p = projection({ table, property, active: true, displayName: label });
  return visualShell(pageKey, key, "slicer", position, {
    query: { queryState: { Values: { projections: [p] } } },
    objects: {
      data: [{ properties: { mode: text("Dropdown") } }],
      selection: [
        {
          properties: {
            selectAllCheckboxEnabled: bool(true),
            singleSelect: bool(false),
            strictSingleSelect: bool(false),
          },
        },
      ],
      header: [
        {
          properties: {
            show: bool(true),
            text: text(label),
            fontFamily: text(FONT),
            textSize: number(9),
            bold: bool(true),
            fontColor: color(COLORS.navy),
            background: color(COLORS.white),
            showRestatement: bool(false),
          },
        },
      ],
    },
    visualContainerObjects: containerObjects(null, { shadow: false }),
  });
}

function navigatorVisual(pageKey, position) {
  const state = (id, fillColor, fontColor, boldValue = false) => ({
    fill: {
      properties: {
        show: bool(true),
        fillColor: color(fillColor),
        transparency: number(0),
      },
      selector: { id },
    },
    text: {
      properties: {
        show: bool(true),
        fontFamily: text(FONT),
        fontSize: number(9),
        bold: bool(boldValue),
        fontColor: color(fontColor),
        verticalAlignment: text("middle"),
        horizontalAlignment: text("center"),
      },
      selector: { id },
    },
    outline: {
      properties: { show: bool(false) },
      selector: { id },
    },
  });
  const defaultState = state("default", COLORS.navy, COLORS.white);
  const hoverState = state("hover", COLORS.navyLight, COLORS.white);
  const selectedState = state("selected", COLORS.orange, COLORS.white, true);
  const disabledState = state("disabled", COLORS.muted, COLORS.headerText);
  return visualShell(pageKey, "page_navigator", "pageNavigator", position, {
    objects: {
      pages: [
        {
          properties: {
            showHiddenPages: bool(false),
            showTooltipPages: bool(false),
            showByDefault: bool(true),
          },
        },
      ],
      layout: [
        {
          properties: {
            orientation: number(0),
            rowCount: integer(1),
            columnCount: integer(5),
            cellPadding: integer(2),
          },
        },
      ],
      shape: [
        {
          properties: {
            tileShape: text("rectangle"),
            roundEdge: integer(0),
          },
        },
      ],
      fill: [
        { ...defaultState.fill, selector: undefined },
        defaultState.fill,
        hoverState.fill,
        selectedState.fill,
        disabledState.fill,
      ],
      text: [
        { ...defaultState.text, selector: undefined },
        defaultState.text,
        hoverState.text,
        selectedState.text,
        disabledState.text,
      ],
      outline: [
        { ...defaultState.outline, selector: undefined },
        defaultState.outline,
        hoverState.outline,
        selectedState.outline,
        disabledState.outline,
      ],
    },
    visualContainerObjects: {
      background: [
        {
          properties: {
            show: bool(true),
            color: color(COLORS.navy),
            transparency: number(0),
          },
        },
      ],
      border: [{ properties: { show: bool(false) } }],
      visualHeader: [{ properties: { show: bool(false) } }],
    },
  });
}

function chartVisual({
  pageKey,
  key,
  type,
  position,
  title: titleValue,
  roles,
  sort,
  colors = [],
  filters = [],
  showLegend = true,
  showAxisTitles = false,
  line = false,
}) {
  const query = { queryState: roles };
  if (sort) {
    query.sortDefinition = {
      sort: [{ field: sort.field, direction: sort.direction }],
      isDefaultSort: false,
    };
  }
  const objects = {
    legend: [
      {
        properties: {
          show: bool(showLegend),
          position: text("Top"),
          showTitle: bool(false),
          fontFamily: text(FONT),
          fontSize: number(9),
          labelColor: color(COLORS.textSecondary),
        },
      },
    ],
    categoryAxis: [
      { properties: { showAxisTitle: bool(showAxisTitles) } },
    ],
    valueAxis: [
      { properties: { showAxisTitle: bool(showAxisTitles) } },
    ],
    dataPoint: [
      {
        properties: {
          defaultColor: color(colors[0]?.color ?? COLORS.orange),
        },
      },
      ...colors.map((item) => ({
        properties: { fill: color(item.color) },
        selector: { metadata: item.queryRef },
      })),
    ],
  };
  if (type !== "scatterChart") {
    objects.labels = [{ properties: { show: bool(false) } }];
  }
  if (line) {
    objects.lineStyles = [
      {
        properties: {
          strokeShow: bool(true),
          strokeWidth: number(2),
          lineStyle: text("solid"),
          showMarker: bool(true),
          markerShape: text("circle"),
          markerSize: number(4),
          lineChartType: text("linear"),
        },
      },
    ];
  }
  if (type === "scatterChart") {
    objects.bubbles = [
      {
        properties: {
          bubbleSize: integer(20),
          markerRangeType: text("auto"),
          preventOverflow: bool(true),
          markerShape: text("circle"),
        },
      },
    ];
    objects.colorByCategory = [
      { properties: { show: bool(false) } },
    ];
  }
  const visual = {
    query,
    objects,
    visualContainerObjects: containerObjects(titleValue),
  };
  return visualShell(pageKey, key, type, position, visual, filters);
}

function tableFormatting() {
  return {
    columnHeaders: [
      {
        properties: {
          fontFamily: text(FONT),
          fontSize: number(9),
          bold: bool(true),
          fontColor: color(COLORS.white),
          backColor: color(COLORS.navy),
          alignment: text("Left"),
          autoSizeColumnWidth: bool(true),
          columnAdjustment: text("fitToContent"),
          wordWrap: bool(true),
        },
      },
    ],
    values: [
      {
        properties: {
          fontFamily: text(FONT),
          fontSize: number(9),
          fontColorPrimary: color(COLORS.text),
          backColorPrimary: color(COLORS.white),
          fontColorSecondary: color(COLORS.text),
          backColorSecondary: color(COLORS.band),
          wordWrap: bool(true),
        },
      },
    ],
    grid: [
      {
        properties: {
          gridVertical: bool(false),
          gridHorizontal: bool(true),
          gridHorizontalColor: color(COLORS.grid),
          gridHorizontalWeight: number(1),
          rowPadding: number(4),
        },
      },
    ],
  };
}

function tableVisual({
  pageKey,
  key,
  position,
  title: titleValue,
  fields,
  sort,
  filters = [],
}) {
  const query = {
    queryState: {
      Values: { projections: fields.map(projection) },
    },
  };
  if (sort) {
    query.sortDefinition = {
      sort: [{ field: sort.field, direction: sort.direction }],
      isDefaultSort: false,
    };
  }
  const visual = {
    query,
    objects: tableFormatting(),
    visualContainerObjects: containerObjects(titleValue),
  };
  return visualShell(pageKey, key, "tableEx", position, visual, filters);
}

function matrixVisual({
  pageKey,
  key,
  position,
  title: titleValue,
  rows = [],
  columns = [],
  values,
  filters = [],
}) {
  const objects = tableFormatting();
  objects.rowHeaders = [
    {
      properties: {
        fontFamily: text(FONT),
        fontSize: number(9),
        bold: bool(true),
        fontColor: color(COLORS.text),
        backColor: color(COLORS.band),
        stepped: bool(false),
        wordWrap: bool(true),
      },
    },
  ];
  const visual = {
    query: {
      queryState: {
        Rows: { projections: rows.map(projection) },
        Columns: { projections: columns.map(projection) },
        Values: { projections: values.map(projection) },
      },
    },
    objects,
    visualContainerObjects: containerObjects(titleValue),
  };
  if (!rows.length) delete visual.query.queryState.Rows;
  if (!columns.length) delete visual.query.queryState.Columns;
  return visualShell(pageKey, key, "pivotTable", position, visual, filters);
}

function addHeader(page, pageKey, pageTitle, subtitle, includeNavigator = true) {
  page.visuals.push(
    shapeVisual(
      pageKey,
      "header_background",
      { x: 0, y: 0, z: 1, height: 70, width: 1280 },
      "rectangle",
      COLORS.navy,
    ),
    shapeVisual(
      pageKey,
      "header_accent",
      { x: 0, y: 64, z: 2, height: 12, width: 1280 },
      "line",
      COLORS.orange,
    ),
    textboxVisual(
      pageKey,
      "header_title",
      { x: 24, y: 0, z: 3, height: 45, width: 700 },
      [{ value: pageTitle, size: 18, bold: true, color: COLORS.white }],
    ),
    textboxVisual(
      pageKey,
      "header_subtitle",
      { x: 24, y: 34, z: 4, height: 34, width: 900 },
      [{ value: `K-APT AX Control Tower · ${subtitle}`, size: 9, color: COLORS.headerText }],
    ),
  );
  if (includeNavigator) {
    page.visuals.push(
      navigatorVisual(pageKey, {
        x: 0,
        y: 70,
        z: 5,
        height: 34,
        width: 1280,
      }),
    );
  }
}

function newPage(key, displayName, options = {}) {
  return {
    key,
    id: pageId(key),
    displayName,
    hidden: options.hidden ?? false,
    visuals: [],
  };
}

function buildExecutiveOverview() {
  const pageKey = "executive-overview";
  const page = newPage(pageKey, "01 Executive Overview");
  addHeader(
    page,
    pageKey,
    "01 Executive Overview",
    "경영진 요약 및 Advisory 우선순위 진단",
  );

  const cardY = 112;
  const cards = [
    ["annual_cost", "대상단지 연환산 관리비", "연환산 관리비", COLORS.navy],
    ["opportunity", "지표상 연간 기회금액", "지표상 기회금액", COLORS.orange],
    ["opportunity_rate", "기회금액률", "기회금액률", COLORS.orange],
    ["priority_count", "P1 P2 항목 수", "P1·P2 항목", COLORS.red],
    ["alert_months", "경보 월 수", "경보 월", COLORS.red],
  ];
  cards.forEach(([key, metric, label, accent], index) => {
    page.visuals.push(
      cardVisual(
        pageKey,
        key,
        { x: 24 + index * 196, y: cardY, z: 100 + index, height: 84, width: 184 },
        metric,
        label,
        accent,
      ),
    );
  });
  page.visuals.push(
    slicerVisual(
      pageKey,
      "category_filter",
      { x: 1004, y: cardY, z: 106, height: 84, width: 252 },
      "DimCostCategory",
      "cost_category_name_ko",
      "비용항목",
    ),
  );

  const category = projection({
    table: "DimCostCategory",
    property: "cost_category_name_ko",
    active: true,
    displayName: "비용항목",
  });
  const targetAnnual = projection({
    table: "_Measures",
    property: "대상 연간 세대당 비용",
    kind: "measure",
  });
  const expectedMedian = projection({
    table: "_Measures",
    property: "기대 중앙값 세대당 비용",
    kind: "measure",
  });
  page.visuals.push(
    chartVisual({
      pageKey,
      key: "target_vs_expected",
      type: "clusteredBarChart",
      position: { x: 24, y: 210, z: 120, height: 252, width: 600 },
      title: "비용항목별 대상단지 vs 기대 중앙값",
      roles: {
        Category: { projections: [category] },
        Y: { projections: [targetAnnual, expectedMedian] },
        Tooltips: {
          projections: [
            projection({ table: "_Measures", property: "기대 하단 세대당 비용", kind: "measure" }),
            projection({ table: "_Measures", property: "기대 상단 세대당 비용", kind: "measure" }),
            projection({ table: "_Measures", property: "연간 비교군 격차율", kind: "measure" }),
          ],
        },
      },
      sort: { field: targetAnnual.field, direction: "Descending" },
      colors: [
        { queryRef: targetAnnual.queryRef, color: COLORS.orange },
        { queryRef: expectedMedian.queryRef, color: COLORS.navy },
      ],
    }),
    chartVisual({
      pageKey,
      key: "anomaly_trend",
      type: "lineChart",
      position: { x: 640, y: 210, z: 121, height: 252, width: 616 },
      title: "월별 비용항목 이상징후 추이",
      roles: {
        Category: {
          projections: [
            projection({ table: "DimDate", property: "YearMonth", active: true, displayName: "기준월" }),
          ],
        },
        Series: { projections: [category] },
        Y: {
          projections: [
            projection({ table: "_Measures", property: "최대 이상징후 점수", kind: "measure" }),
          ],
        },
      },
      sort: { field: column("DimDate", "YearMonth"), direction: "Ascending" },
      colors: [{ color: COLORS.orange }],
      line: true,
    }),
  );

  page.visuals.push(
    matrixVisual({
      pageKey,
      key: "priority_matrix",
      position: { x: 24, y: 478, z: 130, height: 164, width: 1232 },
      title: "비용항목별 Advisory 진단 요약",
      rows: [
        { table: "DimCostCategory", property: "cost_category_name_ko", displayName: "비용항목" },
      ],
      values: [
        { table: "_Measures", property: "연간 비교군 격차율", kind: "measure" },
        { table: "_Measures", property: "최대 이상징후 점수", kind: "measure" },
        { table: "_Measures", property: "Advisory 우선순위 점수", kind: "measure" },
        { table: "_Measures", property: "지표상 연간 기회금액", kind: "measure" },
        { table: "_Measures", property: "경보 월 수", kind: "measure" },
      ],
    }),
    textboxVisual(
      pageKey,
      "responsible_ai_note",
      { x: 24, y: 652, z: 140, height: 48, width: 1232 },
      [
        {
          value:
            "Responsible AI · 본 결과는 공개데이터 기반의 검토 우선순위와 가설을 제시하며 부정행위나 확정 절감액을 판정하지 않습니다. 조치 전 원문 증빙과 담당자 승인이 필요합니다.",
          size: 9,
          bold: true,
          color: COLORS.navy,
        },
      ],
      { background: true, border: true, backgroundColor: COLORS.note, borderColor: COLORS.orange },
    ),
  );
  return page;
}

function buildPeerBenchmark() {
  const pageKey = "peer-benchmark";
  const page = newPage(pageKey, "02 Peer Benchmark");
  addHeader(page, pageKey, "02 Peer Benchmark", "비교단지 선정 근거 및 기대구간 검토");
  const cards = [
    ["peer_count", "선정 비교단지 수", "선정 비교단지", COLORS.navy],
    ["similarity", "가중 평균 유사도", "가중 평균 유사도", COLORS.blue],
    ["coverage", "데이터 관측률", "데이터 관측률", COLORS.green],
    ["readiness", "모델 분석 가능률", "모델 분석 가능률", COLORS.green],
  ];
  cards.forEach(([key, metric, label, accent], index) => {
    page.visuals.push(
      cardVisual(
        pageKey,
        key,
        { x: 24 + index * 246, y: 112, z: 100 + index, height: 84, width: 234 },
        metric,
        label,
        accent,
      ),
    );
  });
  page.visuals.push(
    slicerVisual(
      pageKey,
      "category_filter",
      { x: 1008, y: 112, z: 105, height: 84, width: 248 },
      "DimCostCategory",
      "cost_category_name_ko",
      "비용항목",
    ),
  );

  const peerName = projection({
    table: "ModelPeerWeights",
    property: "apartment_name",
    displayName: "비교단지",
  });
  const similarity = projection({
    table: "ModelPeerWeights",
    property: "structural_similarity_score",
    kind: "aggregation",
    fn: 4,
    displayName: "구조 유사도",
  });
  const suitability = projection({
    table: "ModelPeerWeights",
    property: "peer_suitability_score",
    kind: "aggregation",
    fn: 4,
    displayName: "비교 적합도",
  });
  const householdSize = projection({
    table: "ModelPeerWeights",
    property: "household_count",
    kind: "aggregation",
    fn: 4,
    displayName: "세대수",
  });
  page.visuals.push(
    chartVisual({
      pageKey,
      key: "peer_scatter",
      type: "scatterChart",
      position: { x: 24, y: 210, z: 120, height: 294, width: 610 },
      title: "선정 비교단지 유사도·적합도 분포",
      roles: {
        Category: { projections: [peerName] },
        Series: {
          projections: [
            projection({ table: "ModelPeerWeights", property: "peer_group_class", displayName: "Peer Group" }),
          ],
        },
        X: { projections: [similarity] },
        Y: { projections: [suitability] },
        Size: { projections: [householdSize] },
        Tooltips: {
          projections: [
            projection({ table: "ModelPeerWeights", property: "approval_year", kind: "aggregation", fn: 4, displayName: "사용승인연도" }),
            projection({ table: "ModelPeerWeights", property: "cost_data_coverage_pct", kind: "aggregation", fn: 4, displayName: "비용 데이터 커버리지" }),
            projection({ table: "ModelPeerWeights", property: "model_weight", kind: "aggregation", fn: 4, displayName: "모델 가중치" }),
          ],
        },
      },
      colors: [{ color: COLORS.blue }],
      showAxisTitles: true,
      filters: [
        categoricalFilter(
          pageKey,
          "peer_scatter_selected_peers",
          "ModelPeerWeights",
          "model_selected",
          true,
        ),
      ],
    }),
    chartVisual({
      pageKey,
      key: "expected_range",
      type: "clusteredBarChart",
      position: { x: 650, y: 210, z: 121, height: 294, width: 606 },
      title: "비용항목별 대상값 및 기대구간",
      roles: {
        Category: {
          projections: [
            projection({ table: "DimCostCategory", property: "cost_category_name_ko", active: true, displayName: "비용항목" }),
          ],
        },
        Y: {
          projections: [
            projection({ table: "_Measures", property: "대상 연간 세대당 비용", kind: "measure" }),
            projection({ table: "_Measures", property: "기대 하단 세대당 비용", kind: "measure" }),
            projection({ table: "_Measures", property: "기대 중앙값 세대당 비용", kind: "measure" }),
            projection({ table: "_Measures", property: "기대 상단 세대당 비용", kind: "measure" }),
          ],
        },
      },
      colors: [
        { queryRef: "_Measures.대상 연간 세대당 비용", color: COLORS.orange },
        { queryRef: "_Measures.기대 하단 세대당 비용", color: COLORS.green },
        { queryRef: "_Measures.기대 중앙값 세대당 비용", color: COLORS.navy },
        { queryRef: "_Measures.기대 상단 세대당 비용", color: COLORS.blue },
      ],
    }),
    tableVisual({
      pageKey,
      key: "peer_detail",
      position: { x: 24, y: 520, z: 130, height: 180, width: 1232 },
      title: "선정 비교단지 상세 근거",
      fields: [
        { table: "ModelPeerWeights", property: "peer_rank", displayName: "순위" },
        { table: "ModelPeerWeights", property: "apartment_name", displayName: "비교단지" },
        { table: "ModelPeerWeights", property: "city_district", displayName: "자치구" },
        { table: "ModelPeerWeights", property: "household_count", displayName: "세대수" },
        { table: "ModelPeerWeights", property: "approval_year", displayName: "사용승인연도" },
        { table: "ModelPeerWeights", property: "structural_similarity_score", displayName: "구조 유사도" },
        { table: "ModelPeerWeights", property: "peer_suitability_score", displayName: "적합도" },
        { table: "ModelPeerWeights", property: "model_weight", displayName: "모델 가중치" },
        { table: "ModelPeerWeights", property: "selection_policy", displayName: "선정 정책" },
      ],
      sort: { field: column("ModelPeerWeights", "peer_rank"), direction: "Ascending" },
      filters: [
        categoricalFilter(
          pageKey,
          "peer_detail_selected_peers",
          "ModelPeerWeights",
          "model_selected",
          true,
        ),
      ],
    }),
  );
  return page;
}

function buildCostDriverTrend() {
  const pageKey = "cost-driver-trend";
  const page = newPage(pageKey, "03 Cost Driver & Trend");
  addHeader(page, pageKey, "03 Cost Driver & Trend", "대상단지·비교군 관리비 추이와 비용동인 분석");
  const cards = [
    ["target_total", "대상 관리비 총액", "대상 관리비 총액", COLORS.orange],
    ["target_avg", "대상 월평균 세대당 항목비", "대상 월평균 세대당", COLORS.orange],
    ["peer_avg", "비교군 월평균 세대당 항목비", "비교군 월평균 세대당", COLORS.navy],
    ["gap", "연간 비교군 격차율", "연간 비교군 격차율", COLORS.red],
  ];
  cards.forEach(([key, metric, label, accent], index) => {
    page.visuals.push(
      cardVisual(
        pageKey,
        key,
        { x: 24 + index * 224, y: 112, z: 100 + index, height: 84, width: 212 },
        metric,
        label,
        accent,
      ),
    );
  });
  page.visuals.push(
    slicerVisual(
      pageKey,
      "month_filter",
      { x: 920, y: 112, z: 105, height: 84, width: 158 },
      "DimDate",
      "YearMonth",
      "기준월",
    ),
    slicerVisual(
      pageKey,
      "category_filter",
      { x: 1090, y: 112, z: 106, height: 84, width: 166 },
      "DimCostCategory",
      "cost_category_name_ko",
      "비용항목",
    ),
  );

  const target = projection({
    table: "_Measures",
    property: "대상 월평균 세대당 항목비",
    kind: "measure",
  });
  const peer = projection({
    table: "_Measures",
    property: "비교군 월평균 세대당 항목비",
    kind: "measure",
  });
  page.visuals.push(
    chartVisual({
      pageKey,
      key: "monthly_target_peer",
      type: "lineChart",
      position: { x: 24, y: 210, z: 120, height: 294, width: 760 },
      title: "월별 대상단지 vs 비교군 세대당 관리비",
      roles: {
        Category: {
          projections: [
            projection({ table: "DimDate", property: "YearMonth", active: true, displayName: "기준월" }),
          ],
        },
        Y: { projections: [target, peer] },
      },
      sort: { field: column("DimDate", "YearMonth"), direction: "Ascending" },
      colors: [
        { queryRef: target.queryRef, color: COLORS.orange },
        { queryRef: peer.queryRef, color: COLORS.navy },
      ],
      line: true,
    }),
    chartVisual({
      pageKey,
      key: "category_gap",
      type: "clusteredBarChart",
      position: { x: 800, y: 210, z: 121, height: 294, width: 456 },
      title: "비용항목별 연간 대상값·기대값",
      roles: {
        Category: {
          projections: [
            projection({ table: "DimCostCategory", property: "cost_category_name_ko", active: true, displayName: "비용항목" }),
          ],
        },
        Y: {
          projections: [
            projection({ table: "_Measures", property: "대상 연간 세대당 비용", kind: "measure" }),
            projection({ table: "_Measures", property: "기대 중앙값 세대당 비용", kind: "measure" }),
          ],
        },
      },
      colors: [
        { queryRef: "_Measures.대상 연간 세대당 비용", color: COLORS.orange },
        { queryRef: "_Measures.기대 중앙값 세대당 비용", color: COLORS.navy },
      ],
    }),
    matrixVisual({
      pageKey,
      key: "cost_heatmap",
      position: { x: 24, y: 520, z: 130, height: 180, width: 1232 },
      title: "비용항목·기준월별 대상단지 세대당 관리비",
      rows: [
        { table: "DimCostCategory", property: "cost_category_name_ko", displayName: "비용항목" },
      ],
      columns: [{ table: "DimDate", property: "YearMonth", displayName: "기준월" }],
      values: [
        { table: "_Measures", property: "대상 월평균 세대당 항목비", kind: "measure" },
      ],
    }),
  );
  return page;
}

function buildAnomalyExplorer() {
  const pageKey = "anomaly-explorer";
  const page = newPage(pageKey, "04 Anomaly Explorer");
  addHeader(page, pageKey, "04 Anomaly Explorer", "월별 이상징후 강도·지속성·근거 탐색");
  const cards = [
    ["alerts", "경보 월 수", "경보 월", COLORS.red],
    ["max_score", "최대 이상징후 점수", "최대 이상징후", COLORS.red],
    ["avg_score", "평균 이상징후 점수", "평균 이상징후", COLORS.orange],
    ["readiness", "모델 분석 가능률", "모델 분석 가능률", COLORS.green],
  ];
  cards.forEach(([key, metric, label, accent], index) => {
    page.visuals.push(
      cardVisual(
        pageKey,
        key,
        { x: 24 + index * 206, y: 112, z: 100 + index, height: 84, width: 194 },
        metric,
        label,
        accent,
      ),
    );
  });
  page.visuals.push(
    slicerVisual(
      pageKey,
      "category_filter",
      { x: 848, y: 112, z: 105, height: 84, width: 132 },
      "DimCostCategory",
      "cost_category_name_ko",
      "비용항목",
    ),
    slicerVisual(
      pageKey,
      "severity_filter",
      { x: 990, y: 112, z: 106, height: 84, width: 126 },
      "FactAnomalyMonthly",
      "anomaly_severity",
      "심각도",
    ),
    slicerVisual(
      pageKey,
      "alert_filter",
      { x: 1126, y: 112, z: 107, height: 84, width: 130 },
      "FactAnomalyMonthly",
      "is_alert",
      "경보 여부",
    ),
  );
  page.visuals.push(
    chartVisual({
      pageKey,
      key: "anomaly_line",
      type: "lineChart",
      position: { x: 24, y: 210, z: 120, height: 294, width: 760 },
      title: "비용항목별 월간 이상징후 점수",
      roles: {
        Category: {
          projections: [
            projection({ table: "DimDate", property: "YearMonth", active: true, displayName: "기준월" }),
          ],
        },
        Series: {
          projections: [
            projection({ table: "DimCostCategory", property: "cost_category_name_ko", displayName: "비용항목" }),
          ],
        },
        Y: {
          projections: [
            projection({ table: "_Measures", property: "최대 이상징후 점수", kind: "measure" }),
          ],
        },
      },
      sort: { field: column("DimDate", "YearMonth"), direction: "Ascending" },
      colors: [{ color: COLORS.red }],
      line: true,
    }),
    matrixVisual({
      pageKey,
      key: "anomaly_heatmap",
      position: { x: 800, y: 210, z: 121, height: 294, width: 456 },
      title: "이상징후 Heatmap",
      rows: [
        { table: "DimCostCategory", property: "cost_category_name_ko", displayName: "비용항목" },
      ],
      columns: [{ table: "DimDate", property: "YearMonth", displayName: "기준월" }],
      values: [{ table: "_Measures", property: "최대 이상징후 점수", kind: "measure" }],
    }),
    tableVisual({
      pageKey,
      key: "anomaly_detail",
      position: { x: 24, y: 520, z: 130, height: 180, width: 1232 },
      title: "월별 이상징후 상세 근거",
      fields: [
        { table: "FactAnomalyMonthly", property: "month_start_date", displayName: "기준월" },
        { table: "FactAnomalyMonthly", property: "cost_category_name_ko", displayName: "비용항목" },
        { table: "_Measures", property: "대상 월 세대당 비용", kind: "measure", displayName: "대상 세대당 비용" },
        { table: "FactAnomalyMonthly", property: "peer_median_krw", displayName: "비교군 중앙값" },
        { table: "FactAnomalyMonthly", property: "gap_pct", displayName: "격차율(%)" },
        { table: "FactAnomalyMonthly", property: "anomaly_score", displayName: "이상징후 점수" },
        { table: "FactAnomalyMonthly", property: "anomaly_severity", displayName: "심각도" },
        { table: "FactAnomalyMonthly", property: "is_alert", displayName: "경보" },
        { table: "FactAnomalyMonthly", property: "anomaly_reason", displayName: "탐지 근거" },
      ],
      sort: { field: column("FactAnomalyMonthly", "month_start_date"), direction: "Descending" },
    }),
  );
  return page;
}

function buildActionCenter() {
  const pageKey = "action-center";
  const page = newPage(pageKey, "05 Advisory Action Center");
  addHeader(page, pageKey, "05 Advisory Action Center", "AX 과제·증빙 요청·사람 승인 중심 실행관리");
  const cards = [
    ["opportunity", "지표상 연간 기회금액", "기회금액", COLORS.orange],
    ["p12", "P1 P2 항목 수", "P1·P2 항목", COLORS.red],
    ["actions", "조치 과제 수", "조치 과제", COLORS.navy],
    ["evidence", "증빙 요청 수", "증빙 요청", COLORS.blue],
    ["approval", "사람 승인 필요 과제 수", "사람 승인 필요", COLORS.red],
  ];
  cards.forEach(([key, metric, label, accent], index) => {
    page.visuals.push(
      cardVisual(
        pageKey,
        key,
        { x: 24 + index * 148, y: 112, z: 100 + index, height: 84, width: 136 },
        metric,
        label,
        accent,
      ),
    );
  });
  const slicers = [
    ["priority_filter", "FactAdvisoryAssessment", "advisory_priority", "우선순위"],
    ["category_filter", "DimCostCategory", "cost_category_name_ko", "비용항목"],
    ["action_status_filter", "FactActionRegister", "action_status", "과제 상태"],
    ["evidence_status_filter", "FactEvidenceRequest", "request_status", "증빙 상태"],
  ];
  slicers.forEach(([key, table, property, label], index) => {
    page.visuals.push(
      slicerVisual(
        pageKey,
        key,
        { x: 764 + index * 124, y: 112, z: 106 + index, height: 84, width: 112 },
        table,
        property,
        label,
      ),
    );
  });
  page.visuals.push(
    tableVisual({
      pageKey,
      key: "assessment_table",
      position: { x: 24, y: 210, z: 120, height: 150, width: 1232 },
      title: "Advisory 진단 및 우선순위",
      fields: [
        { table: "FactAdvisoryAssessment", property: "advisory_priority", displayName: "우선순위" },
        { table: "FactAdvisoryAssessment", property: "advisory_priority_score", displayName: "점수" },
        { table: "FactAdvisoryAssessment", property: "cost_category_name_ko", displayName: "비용항목" },
        { table: "FactAdvisoryAssessment", property: "screened_pain_point", displayName: "검토 Pain Point" },
        { table: "FactAdvisoryAssessment", property: "primary_recommended_action", displayName: "권고 조치" },
        { table: "FactAdvisoryAssessment", property: "indicative_annual_opportunity_krw", displayName: "지표상 기회금액" },
        { table: "FactAdvisoryAssessment", property: "confidence_level", displayName: "신뢰수준" },
        { table: "FactAdvisoryAssessment", property: "human_validation_required", displayName: "사람 검증" },
      ],
      sort: { field: column("FactAdvisoryAssessment", "advisory_priority_rank"), direction: "Ascending" },
    }),
    tableVisual({
      pageKey,
      key: "action_register",
      position: { x: 24, y: 374, z: 121, height: 150, width: 1232 },
      title: "AX 조치 과제 Register",
      fields: [
        { table: "FactActionRegister", property: "advisory_priority", displayName: "우선순위" },
        { table: "FactActionRegister", property: "action_sequence", displayName: "순서" },
        { table: "FactActionRegister", property: "cost_category_name_ko", displayName: "비용항목" },
        { table: "FactActionRegister", property: "action_title", displayName: "조치 과제" },
        { table: "FactActionRegister", property: "business_owner", displayName: "담당" },
        { table: "FactActionRegister", property: "time_horizon", displayName: "기간" },
        { table: "FactActionRegister", property: "success_kpi", displayName: "성공 KPI" },
        { table: "FactActionRegister", property: "digital_enablement", displayName: "Digital Enablement" },
        { table: "FactActionRegister", property: "action_status", displayName: "상태" },
        { table: "FactActionRegister", property: "human_approval_required", displayName: "사람 승인" },
      ],
      sort: { field: column("FactActionRegister", "category_priority_rank"), direction: "Ascending" },
    }),
    tableVisual({
      pageKey,
      key: "evidence_requests",
      position: { x: 24, y: 538, z: 122, height: 118, width: 1232 },
      title: "증빙 요청 및 개인정보 검토",
      fields: [
        { table: "FactEvidenceRequest", property: "evidence_priority", displayName: "우선순위" },
        { table: "FactEvidenceRequest", property: "cost_category_name_ko", displayName: "비용항목" },
        { table: "FactEvidenceRequest", property: "document_name", displayName: "요청 문서" },
        { table: "FactEvidenceRequest", property: "request_purpose", displayName: "요청 목적" },
        { table: "FactEvidenceRequest", property: "expected_provider", displayName: "제공 주체" },
        { table: "FactEvidenceRequest", property: "request_status", displayName: "상태" },
        { table: "FactEvidenceRequest", property: "contains_personal_data_review", displayName: "개인정보 검토" },
      ],
    }),
    textboxVisual(
      pageKey,
      "human_in_loop_note",
      { x: 24, y: 666, z: 130, height: 34, width: 1232 },
      [
        {
          value:
            "Human-in-the-loop · 모든 권고는 증빙 수집 → 담당자 검토 → 입주자대표회의/관리주체 승인 후 실행합니다. 자동 집행은 허용하지 않습니다.",
          size: 9,
          bold: true,
          color: COLORS.red,
        },
      ],
      { background: true, border: true, backgroundColor: "#FEF2F2", borderColor: COLORS.red },
    ),
  );
  return page;
}

function buildModelQa() {
  const pageKey = "model-qa";
  const page = newPage(pageKey, "00 Model QA", { hidden: true });
  addHeader(page, pageKey, "00 Model QA", "데이터 커버리지·모델 입력·지표 정합성 검증", false);
  const cards = [
    ["apartments", "Apartment Count", "서울 단지 수", COLORS.navy, "DimApartmentMaster"],
    ["districts", "District Count", "자치구 수", COLORS.navy, "DimApartmentMaster"],
    ["monthly_rows", "월별 팩트 행 수", "월별 Fact 행", COLORS.blue, "_Measures"],
    ["categories", "비용항목 수", "비용항목", COLORS.blue, "_Measures"],
    ["peers", "선정 비교단지 수", "선정 비교단지", COLORS.orange, "_Measures"],
    ["coverage", "데이터 관측률", "데이터 관측률", COLORS.green, "_Measures"],
    ["readiness", "모델 분석 가능률", "모델 분석 가능률", COLORS.green, "_Measures"],
    ["actions", "조치 과제 수", "조치 과제", COLORS.purple, "_Measures"],
  ];
  cards.forEach(([key, metric, label, accent, table], index) => {
    const x = 24 + (index % 4) * 308;
    const y = 86 + Math.floor(index / 4) * 98;
    if (table === "_Measures") {
      page.visuals.push(
        cardVisual(pageKey, key, { x, y, z: 100 + index, height: 84, width: 292 }, metric, label, accent),
      );
    } else {
      const p = projection({ table, property: metric, kind: "measure", displayName: label });
      const card = cardVisual(
        pageKey,
        key,
        { x, y, z: 100 + index, height: 84, width: 292 },
        "월별 팩트 행 수",
        label,
        accent,
      );
      card.visual.query.queryState.Data.projections = [p];
      page.visuals.push(card);
    }
  });
  page.visuals.push(
    matrixVisual({
      pageKey,
      key: "qa_matrix",
      position: { x: 24, y: 294, z: 120, height: 340, width: 1232 },
      title: "비용항목별 모델 결과 Reconciliation",
      rows: [
        { table: "DimCostCategory", property: "cost_category_name_ko", displayName: "비용항목" },
      ],
      values: [
        { table: "_Measures", property: "대상 연간 세대당 비용", kind: "measure" },
        { table: "_Measures", property: "기대 하단 세대당 비용", kind: "measure" },
        { table: "_Measures", property: "기대 중앙값 세대당 비용", kind: "measure" },
        { table: "_Measures", property: "기대 상단 세대당 비용", kind: "measure" },
        { table: "_Measures", property: "연간 비교군 격차율", kind: "measure" },
        { table: "_Measures", property: "최대 이상징후 점수", kind: "measure" },
        { table: "_Measures", property: "Advisory 우선순위 점수", kind: "measure" },
      ],
    }),
    textboxVisual(
      pageKey,
      "qa_note",
      { x: 24, y: 646, z: 130, height: 54, width: 1232 },
      [
        {
          value:
            "QA 기준 · 50개 Pilot 단지 × 12개월 × 6개 비용항목 = 3,600행. 비용항목별 기대구간·이상징후·Advisory 결과가 모두 조회되어야 합니다.",
          size: 9,
          bold: true,
          color: COLORS.navy,
        },
      ],
      { background: true, border: true, backgroundColor: "#EFF6FF", borderColor: COLORS.blue },
    ),
  );
  return page;
}

function writeJson(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function writePage(page) {
  const pagePath = path.join(pagesDir, page.id);
  writeJson(path.join(pagePath, "page.json"), {
    $schema: PAGE_SCHEMA,
    name: page.id,
    displayName: page.displayName,
    displayOption: "FitToPage",
    height: 720,
    width: 1280,
    ...(page.hidden ? { visibility: "HiddenInViewMode" } : {}),
    objects: pageObjects(),
  });
  for (const visual of page.visuals) {
    writeJson(
      path.join(pagePath, "visuals", visual.name, "visual.json"),
      visual,
    );
  }
}

function replacePages(pages) {
  const safePagesDir = path.resolve(pagesDir);
  if (!safePagesDir.endsWith(path.join("definition", "pages"))) {
    throw new Error(`Refusing to replace unexpected directory: ${safePagesDir}`);
  }
  for (const entry of fs.readdirSync(safePagesDir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      fs.rmSync(path.join(safePagesDir, entry.name), {
        recursive: true,
        force: true,
      });
    }
  }
  pages.forEach(writePage);
  writeJson(path.join(safePagesDir, "pages.json"), {
    $schema: PAGES_SCHEMA,
    pageOrder: pages.map((page) => page.id),
    activePageName: pages[0].id,
  });
}

function repairDefinitionPbir() {
  const pbirPath = path.join(reportDir, "definition.pbir");
  const definition = JSON.parse(fs.readFileSync(pbirPath, "utf8"));
  writeJson(pbirPath, { $schema: PBIR_SCHEMA, ...definition });
}

function updateThemes() {
  const sourceThemePath = path.join(
    repoRoot,
    "powerbi",
    "theme",
    "kapt_ax_advisory_theme.json",
  );
  const resourceName = "K-APT_AX_Advisory8625404744511584.json";
  const registeredThemePath = path.join(
    reportDir,
    "StaticResources",
    "RegisteredResources",
    resourceName,
  );
  const baseTheme = {
    name: "K-APT AX Advisory",
    dataColors: [
      COLORS.orange,
      COLORS.navy,
      COLORS.blue,
      COLORS.green,
      COLORS.red,
      COLORS.purple,
      COLORS.teal,
      COLORS.muted,
    ],
    background: COLORS.page,
    foreground: COLORS.text,
    tableAccent: COLORS.orange,
    good: COLORS.green,
    neutral: COLORS.yellow,
    bad: COLORS.red,
    minimum: COLORS.green,
    center: COLORS.page,
    maximum: COLORS.red,
    textClasses: {
      callout: { fontFace: FONT, fontSize: 24, color: COLORS.navy },
      title: { fontFace: FONT, fontSize: 12, color: COLORS.navy },
      header: { fontFace: FONT, fontSize: 10, color: COLORS.text },
      label: { fontFace: FONT, fontSize: 9, color: COLORS.textSecondary },
    },
  };
  writeJson(sourceThemePath, baseTheme);
  writeJson(registeredThemePath, { ...baseTheme, name: resourceName });
}

const pages = [
  buildExecutiveOverview(),
  buildPeerBenchmark(),
  buildCostDriverTrend(),
  buildAnomalyExplorer(),
  buildActionCenter(),
  buildModelQa(),
];

replacePages(pages);
repairDefinitionPbir();
updateThemes();

console.log(`[OK] Generated ${pages.length} Power BI pages.`);
console.log(
  `[OK] Visible pages: ${pages.filter((page) => !page.hidden).length}; hidden QA pages: ${pages.filter((page) => page.hidden).length}.`,
);
console.log(`[OK] Report directory: ${reportDir}`);
