package rw.nisr.doubleexclusion;

import android.app.Activity;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.Region;
import android.graphics.Typeface;
import android.graphics.RectF;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.ViewConfiguration;
import android.widget.ArrayAdapter;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.text.NumberFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Offline-first Android companion for the public EICV7 district aggregates. */
public final class MainActivity extends Activity {
    private static final int NAVY = Color.rgb(23, 54, 93);
    private static final int TEAL = Color.rgb(8, 126, 139);
    private static final int INK = Color.rgb(29, 41, 53);
    private static final int MUTED = Color.rgb(102, 116, 130);
    private static final int BG = Color.rgb(245, 247, 250);
    private static final int LINE = Color.rgb(226, 232, 238);
    private static final int GOLD = Color.rgb(199, 126, 39);

    private final List<District> districts = new ArrayList<>();
    private final Map<String, District> byCode = new HashMap<>();
    private List<Boundary> boundaries = new ArrayList<>();
    private int metricIndex = 0;
    private String query = "";
    private LinearLayout districtList;
    private TextView listCount;
    private MapView mapView;
    private boolean detailOpen = false;

    private static final String[] METRICS = {
            "Double exclusion rate",
            "Estimated households with neither",
            "VUP coverage among poor households",
            "Bank or mobile account access",
            "Poverty rate"
    };

    @Override
    public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(NAVY);
        getWindow().setNavigationBarColor(BG);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        try {
            loadDistricts();
            loadBoundaries();
            showHome();
        } catch (Exception error) {
            showLoadError(error);
        }
    }

    @Override
    public void onBackPressed() {
        if (detailOpen) showHome();
        else super.onBackPressed();
    }

    private void loadDistricts() throws Exception {
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(
                getAssets().open("district_estimates.csv"), StandardCharsets.UTF_8))) {
            String first = reader.readLine();
            if (first == null) throw new IllegalStateException("The district CSV is empty.");
            List<String> headers = parseCsv(first);
            Map<String, Integer> ix = new HashMap<>();
            for (int i = 0; i < headers.size(); i++) ix.put(headers.get(i).replace("\uFEFF", ""), i);
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.trim().isEmpty()) continue;
                List<String> cells = parseCsv(line);
                District d = new District();
                d.code = value(cells, ix, "district_code");
                d.name = value(cells, ix, "district");
                d.samplePoor = integer(cells, ix, "sample_poor_households");
                d.poorHouseholds = number(cells, ix, "estimated_poor_households");
                d.population = number(cells, ix, "estimated_population");
                d.poorPopulation = number(cells, ix, "estimated_poor_population");
                d.poverty = number(cells, ix, "poverty_rate");
                d.vup = number(cells, ix, "vup_coverage_among_poor");
                d.finance = number(cells, ix, "financial_access_among_poor");
                d.exclusion = number(cells, ix, "double_exclusion_among_poor");
                d.exclusionLow = number(cells, ix, "double_exclusion_among_poor_ci_low");
                d.exclusionHigh = number(cells, ix, "double_exclusion_among_poor_ci_high");
                d.excludedHouseholds = number(cells, ix, "estimated_double_excluded_poor_households");
                d.reliability = value(cells, ix, "reliability_flag");
                districts.add(d);
                byCode.put(d.code, d);
            }
        }
        if (districts.isEmpty()) throw new IllegalStateException("No district rows were found.");
    }

    private void loadBoundaries() throws Exception {
        StringBuilder json = new StringBuilder();
        try (InputStream stream = getAssets().open("district_boundaries.geojson");
             BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) json.append(line);
        }
        JSONObject root = new JSONObject(json.toString());
        JSONArray features = root.getJSONArray("features");
        for (int i = 0; i < features.length(); i++) {
            JSONObject feature = features.getJSONObject(i);
            JSONObject properties = feature.getJSONObject("properties");
            District district = byCode.get(properties.optString("dist_code"));
            if (district == null) continue;
            JSONObject geometry = feature.getJSONObject("geometry");
            String type = geometry.getString("type");
            JSONArray coordinates = geometry.getJSONArray("coordinates");
            Boundary boundary = new Boundary(district);
            if ("Polygon".equals(type)) {
                boundary.addOuterRing(coordinates.getJSONArray(0));
            } else if ("MultiPolygon".equals(type)) {
                for (int p = 0; p < coordinates.length(); p++) {
                    boundary.addOuterRing(coordinates.getJSONArray(p).getJSONArray(0));
                }
            }
            if (!boundary.rings.isEmpty()) boundaries.add(boundary);
        }
    }

    private static List<String> parseCsv(String row) {
        List<String> values = new ArrayList<>();
        StringBuilder cell = new StringBuilder();
        boolean quoted = false;
        for (int i = 0; i < row.length(); i++) {
            char c = row.charAt(i);
            if (c == '"') {
                if (quoted && i + 1 < row.length() && row.charAt(i + 1) == '"') {
                    cell.append('"'); i++;
                } else quoted = !quoted;
            } else if (c == ',' && !quoted) {
                values.add(cell.toString()); cell.setLength(0);
            } else cell.append(c);
        }
        values.add(cell.toString());
        return values;
    }

    private static String value(List<String> row, Map<String, Integer> ix, String name) {
        Integer i = ix.get(name);
        return i == null || i >= row.size() ? "" : row.get(i).trim();
    }

    private static double number(List<String> row, Map<String, Integer> ix, String name) {
        try { return Double.parseDouble(value(row, ix, name)); }
        catch (Exception ignored) { return 0; }
    }

    private static int integer(List<String> row, Map<String, Integer> ix, String name) {
        return (int) Math.round(number(row, ix, name));
    }

    private void showHome() {
        detailOpen = false;
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        LinearLayout page = column();
        page.setPadding(dp(18), dp(18), dp(18), dp(28));
        page.addView(header("RWANDA  /  EICV7 2023â€“24", "Double exclusion", "Explore where poverty and gaps in services overlap across Rwandaâ€™s districts."));
        double weightedPoorHouseholds = 0, weightedPopulation = 0, weightedPoorPopulation = 0;
        double weightedVup = 0, weightedFinance = 0, weightedDoubleExcluded = 0;
        for (District d : districts) {
            weightedPoorHouseholds += d.poorHouseholds;
            weightedPopulation += d.population;
            weightedPoorPopulation += d.poorPopulation;
            weightedVup += d.vup * d.poorHouseholds;
            weightedFinance += d.finance * d.poorHouseholds;
            weightedDoubleExcluded += d.excludedHouseholds;
        }
        double nationalPoverty = weightedPopulation > 0 ? weightedPoorPopulation / weightedPopulation : 0;
        double nationalVup = weightedPoorHouseholds > 0 ? weightedVup / weightedPoorHouseholds : 0;
        double nationalFinance = weightedPoorHouseholds > 0 ? weightedFinance / weightedPoorHouseholds : 0;
        double nationalDoubleExclusion = weightedPoorHouseholds > 0 ? weightedDoubleExcluded / weightedPoorHouseholds : 0;
        page.addView(sectionLabel("National picture"));
        LinearLayout firstKpis = row();
        firstKpis.addView(kpi(String.format(Locale.US, "%.1f%%", nationalDoubleExclusion * 100), "Poor households with neither", "About " + count(weightedDoubleExcluded) + " households", 1), weight());
        firstKpis.addView(kpi(String.format(Locale.US, "%.1f%%", nationalPoverty * 100), "Population in poverty", "Population weighted", 1), weight());
        page.addView(firstKpis);
        LinearLayout secondKpis = row();
        secondKpis.addView(kpi(String.format(Locale.US, "%.1f%%", nationalVup * 100), "VUP coverage among poor", "Household weighted", 2), weight());
        secondKpis.addView(kpi(String.format(Locale.US, "%.1f%%", nationalFinance * 100), "Bank/mobile account access", "Among poor households", 2), weight());
        page.addView(secondKpis);
        TextView denominator = body("Each percentage uses its survey weight and denominator: population for poverty, poor households for program and account coverage.", 12, MUTED);
        denominator.setPadding(dp(2), dp(6), dp(2), dp(10));
        page.addView(denominator);

        page.addView(sectionLabel("District explorer"));
        TextView measureLabel = body("MAP AND RANK BY", 11, TEAL);
        measureLabel.setTypeface(null, Typeface.BOLD);
        measureLabel.setPadding(dp(2), dp(2), 0, dp(5));
        page.addView(measureLabel);
        Spinner metric = new Spinner(this);
        ArrayAdapter<String> metricAdapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, METRICS);
        metricAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        metric.setAdapter(metricAdapter);
        metric.setSelection(metricIndex, false);
        metric.setBackground(rounded(Color.WHITE, LINE, dp(12)));
        page.addView(metric, new LinearLayout.LayoutParams(-1, dp(52)));
        metric.setOnItemSelectedListener(new android.widget.AdapterView.OnItemSelectedListener() {
            @Override public void onItemSelected(android.widget.AdapterView<?> parent, View view, int position, long id) {
                if (metricIndex != position) { metricIndex = position; renderMap(); renderDistricts(); }
            }
            @Override public void onNothingSelected(android.widget.AdapterView<?> parent) { }
        });
        mapView = new MapView();
        LinearLayout mapCard = cardColumn();
        TextView mapTitle = title("District map", 16);
        mapCard.addView(mapTitle);
        mapCard.addView(mapView, new LinearLayout.LayoutParams(-1, dp(250)));
        LinearLayout legend = row();
        legend.setGravity(Gravity.CENTER_VERTICAL);
        legend.addView(colorSwatch(Color.rgb(231, 243, 243)));
        legend.addView(body("Lower", 10, MUTED), new LinearLayout.LayoutParams(0, -2, 1));
        legend.addView(colorSwatch(Color.rgb(95, 160, 164)));
        legend.addView(body("Middle", 10, MUTED), new LinearLayout.LayoutParams(0, -2, 1));
        legend.addView(colorSwatch(NAVY));
        legend.addView(body("Higher", 10, MUTED), new LinearLayout.LayoutParams(0, -2, 1));
        mapCard.addView(legend);
        mapCard.addView(body("Tap a district to view its profile. Shading reflects the selected measure.", 11, MUTED));
        page.addView(mapCard, margins(0, 0, 0, 14));

        LinearLayout searchRow = row();
        EditText search = new EditText(this);
        search.setSingleLine(true);
        search.setHint("Search districts");
        search.setTextSize(14);
        search.setPadding(dp(14), 0, dp(14), 0);
        search.setBackground(rounded(Color.WHITE, LINE, dp(12)));
        searchRow.addView(search, new LinearLayout.LayoutParams(0, dp(48), 1));
        listCount = body("30 districts", 12, MUTED);
        listCount.setGravity(Gravity.CENTER_VERTICAL | Gravity.RIGHT);
        listCount.setPadding(dp(8), 0, 0, 0);
        searchRow.addView(listCount, new LinearLayout.LayoutParams(dp(95), dp(48)));
        page.addView(searchRow);
        districtList = column();
        page.addView(districtList);
        search.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) { }
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) {
                query = s.toString().trim().toLowerCase(Locale.ROOT);
                renderDistricts();
            }
            @Override public void afterTextChanged(Editable s) { }
        });
        page.addView(methodsCard());
        TextView footer = body("Source: NISR EICV7 2023/24 Â· District summaries Â· No household records", 10, MUTED);
        footer.setGravity(Gravity.CENTER);
        footer.setPadding(0, dp(18), 0, 0);
        page.addView(footer);
        scroll.addView(page);
        setContentView(scroll);
        renderMap();
        renderDistricts();
    }

    private void renderMap() {
        if (mapView != null) mapView.invalidate();
    }

    private void renderDistricts() {
        if (districtList == null) return;
        districtList.removeAllViews();
        List<District> filtered = new ArrayList<>();
        for (District d : districts) if (d.name.toLowerCase(Locale.ROOT).contains(query)) filtered.add(d);
        filtered.sort(Comparator.comparingDouble(this::metricValue).reversed());
        listCount.setText(filtered.size() + (filtered.size() == 1 ? " district" : " districts"));
        int rank = 1;
        for (District d : filtered) {
            final District item = d;
            LinearLayout card = row();
            card.setGravity(Gravity.CENTER_VERTICAL);
            card.setPadding(dp(13), dp(12), dp(13), dp(12));
            card.setBackground(rounded(Color.WHITE, LINE, dp(14)));
            TextView rankView = body(String.format(Locale.US, "%02d", rank++), 12, TEAL);
            rankView.setTypeface(null, Typeface.BOLD);
            rankView.setGravity(Gravity.CENTER);
            rankView.setBackground(rounded(Color.rgb(226, 242, 242), Color.TRANSPARENT, dp(10)));
            card.addView(rankView, new LinearLayout.LayoutParams(dp(38), dp(38)));
            LinearLayout names = column();
            names.setPadding(dp(11), 0, dp(8), 0);
            names.addView(title(d.name, 15));
            names.addView(body(String.format(Locale.US, "%.1f%% double exclusion Â· %s households", d.exclusion * 100, count(d.excludedHouseholds)), 11, MUTED));
            card.addView(names, new LinearLayout.LayoutParams(0, -2, 1));
            TextView value = title(formatMetric(d), 15);
            value.setTextColor(NAVY);
            card.addView(value);
            card.setOnClickListener(v -> showDistrict(item));
            districtList.addView(card, margins(0, 0, 0, 7));
        }
    }

    private double metricValue(District d) {
        switch (metricIndex) {
            case 1: return d.excludedHouseholds;
            case 2: return d.vup;
            case 3: return d.finance;
            case 4: return d.poverty;
            default: return d.exclusion;
        }
    }

    private String formatMetric(District d) {
        if (metricIndex == 1) return count(d.excludedHouseholds);
        return String.format(Locale.US, "%.1f%%", metricValue(d) * 100);
    }

    private void showDistrict(District d) {
        detailOpen = true;
        ScrollView scroll = new ScrollView(this);
        LinearLayout page = column();
        page.setPadding(dp(18), dp(56), dp(18), dp(30));
        TextView back = body("<  ALL DISTRICTS", 14, TEAL);
        back.setTypeface(null, Typeface.BOLD);
        back.setGravity(Gravity.CENTER_VERTICAL);
        back.setPadding(dp(14), 0, dp(14), 0);
        back.setMinHeight(dp(48));
        back.setBackground(rounded(Color.WHITE, LINE, dp(12)));
        back.setContentDescription("Back to all districts");
        back.setClickable(true);
        back.setOnClickListener(v -> showHome());
        page.addView(back, margins(0, dp(48), 0, 14));
        page.addView(header("DISTRICT PROFILE", d.name, "EICV7 household estimates Â· Weighted district summary"));
        LinearLayout highlight = cardColumn();
        highlight.addView(body("DOUBLE EXCLUSION AMONG POOR HOUSEHOLDS", 11, TEAL));
        TextView mainRate = title(String.format(Locale.US, "%.1f%%", d.exclusion * 100), 38);
        mainRate.setTextColor(NAVY);
        mainRate.setPadding(0, dp(6), 0, dp(2));
        highlight.addView(mainRate);
        highlight.addView(body(String.format(Locale.US, "Approx. 95%% interval: %.1f%% â€“ %.1f%%", d.exclusionLow * 100, d.exclusionHigh * 100), 13, MUTED));
        highlight.addView(body("Estimated affected poor households: " + count(d.excludedHouseholds), 13, INK));
        page.addView(highlight, margins(0, 0, 0, 14));

        page.addView(sectionLabel("Household access"));
        page.addView(profileRow("VUP participation", d.vup, "Among poor households", TEAL));
        page.addView(profileRow("Bank or mobile account", d.finance, "At least one member has access", NAVY));
        page.addView(profileRow("Neither service observed", d.exclusion, "Among poor households", GOLD));
        page.addView(sectionLabel("Poverty and sample"));
        LinearLayout stats = row();
        stats.addView(kpi(String.format(Locale.US, "%.1f%%", d.poverty * 100), "Population poverty", "Population weighted", 1), weight());
        stats.addView(kpi(count(d.samplePoor), "Poor households sampled", "District sample", 2), weight());
        page.addView(stats);
        if (d.reliability != null && !d.reliability.isEmpty()) {
            TextView caution = body("Interpret with caution: " + d.reliability, 12, GOLD);
            caution.setPadding(dp(12), dp(12), dp(12), dp(12));
            caution.setBackground(rounded(Color.rgb(255, 248, 237), Color.rgb(242, 219, 187), dp(10)));
            page.addView(caution, margins(0, 0, 0, 12));
        }
        page.addView(methodsCard());
        scroll.addView(page);
        setContentView(scroll);
    }

    private View profileRow(String label, double value, String note, int color) {
        LinearLayout card = cardColumn();
        LinearLayout line = row();
        line.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout labels = column();
        labels.addView(title(label, 14));
        labels.addView(body(note, 11, MUTED));
        line.addView(labels, new LinearLayout.LayoutParams(0, -2, 1));
        TextView amount = title(String.format(Locale.US, "%.1f%%", value * 100), 17);
        amount.setTextColor(color);
        line.addView(amount);
        card.addView(line);
        View track = new View(this);
        track.setBackground(rounded(LINE, Color.TRANSPARENT, dp(5)));
        LinearLayout.LayoutParams trackParams = new LinearLayout.LayoutParams(-1, dp(7));
        trackParams.topMargin = dp(11);
        card.addView(track, trackParams);
        View progress = new View(this);
        progress.setBackground(rounded(color, Color.TRANSPARENT, dp(5)));
        LinearLayout.LayoutParams progressParams = new LinearLayout.LayoutParams(0, dp(7));
        progressParams.topMargin = -dp(7);
        progressParams.width = Math.max(dp(8), (int) (getResources().getDisplayMetrics().widthPixels * .82f * Math.max(0, Math.min(1, value))));
        card.addView(progress, progressParams);
        return card;
    }

    private View colorSwatch(int color) {
        View swatch = new View(this);
        swatch.setBackground(rounded(color, Color.TRANSPARENT, dp(4)));
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(dp(17), dp(9));
        p.rightMargin = dp(5);
        return withParams(swatch, p);
    }

    private View methodsCard() {
        LinearLayout card = cardColumn();
        card.addView(title("How to read these estimates", 15));
        card.addView(body("Double exclusion means a poor household has neither an observed VUP participation flag nor a bank/mobile-money account. The survey does not establish VUP eligibility or explain why a household lacks access.", 12, MUTED));
        card.addView(body("The estimates are descriptive and self-reported. They are intended to guide district service reviews, not to identify individual households or measure program impact.", 12, MUTED));
        return card;
    }

    private void showLoadError(Exception error) {
        LinearLayout page = column(); page.setPadding(dp(24), dp(36), dp(24), dp(24));
        page.addView(title("Could not load district data", 22));
        page.addView(body(error.getMessage() == null ? "Check that the district data assets are present." : error.getMessage(), 15, MUTED));
        setContentView(page);
    }

    private View header(String kicker, String heading, String subtitle) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(19), dp(18), dp(19), dp(19));
        android.graphics.drawable.GradientDrawable background = new android.graphics.drawable.GradientDrawable(
                android.graphics.drawable.GradientDrawable.Orientation.TL_BR,
                new int[]{NAVY, Color.rgb(32, 83, 109), TEAL});
        background.setCornerRadius(dp(18)); card.setBackground(background);
        TextView top = body(kicker, 10, Color.rgb(191, 229, 228)); top.setTypeface(null, Typeface.BOLD); card.addView(top);
        TextView name = title(heading, 27); name.setTextColor(Color.WHITE); name.setPadding(0, dp(7), 0, dp(4)); card.addView(name);
        TextView sub = body(subtitle, 13, Color.rgb(225, 235, 240)); card.addView(sub);
        card.setElevation(dp(2));
        LinearLayout.LayoutParams p = margins(0, 0, 0, 17); return withParams(card, p);
    }

    private View kpi(String value, String label, String note, int tone) {
        LinearLayout card = cardColumn();
        TextView v = title(value, 22); v.setTextColor(tone == 2 ? TEAL : NAVY); card.addView(v);
        TextView l = body(label, 12, INK); l.setTypeface(null, Typeface.BOLD); l.setPadding(0, dp(4), 0, dp(2)); card.addView(l);
        card.addView(body(note, 10, MUTED));
        return withParams(card, margins(0, 0, 6, 8));
    }

    private TextView sectionLabel(String value) {
        TextView view = title(value, 17); view.setTextColor(NAVY); view.setPadding(dp(1), dp(10), 0, dp(8)); return view;
    }
    private TextView title(String value, int size) { TextView v = body(value, size, INK); v.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL)); return v; }
    private TextView body(String value, int size, int color) { TextView v = new TextView(this); v.setText(value); v.setTextSize(size); v.setTextColor(color); v.setGravity(Gravity.CENTER_VERTICAL); v.setIncludeFontPadding(false); return v; }
    private LinearLayout column() { LinearLayout l = new LinearLayout(this); l.setOrientation(LinearLayout.VERTICAL); return l; }
    private LinearLayout row() { LinearLayout l = new LinearLayout(this); l.setOrientation(LinearLayout.HORIZONTAL); return l; }
    private LinearLayout cardColumn() { LinearLayout l = column(); l.setPadding(dp(14), dp(13), dp(14), dp(13)); l.setBackground(rounded(Color.WHITE, LINE, dp(14))); l.setElevation(dp(1)); return l; }
    private LinearLayout.LayoutParams weight() { return new LinearLayout.LayoutParams(0, -2, 1); }
    private LinearLayout.LayoutParams margins(int width, int height, int right, int bottom) { LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(width == 0 ? -1 : width, height == 0 ? -2 : height); p.rightMargin = dp(right); p.bottomMargin = dp(bottom); return p; }
    private View withParams(View view, LinearLayout.LayoutParams params) { view.setLayoutParams(params); return view; }
    private int dp(float value) { return (int) (value * getResources().getDisplayMetrics().density + .5f); }
    private android.graphics.drawable.GradientDrawable rounded(int color, int stroke, int radius) { android.graphics.drawable.GradientDrawable d = new android.graphics.drawable.GradientDrawable(); d.setColor(color); d.setCornerRadius(radius); if (stroke != Color.TRANSPARENT) d.setStroke(dp(1), stroke); return d; }
    private String count(double value) { return NumberFormat.getIntegerInstance(Locale.US).format(Math.round(value)); }

    private final class MapView extends View {
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final List<RenderedBoundary> rendered = new ArrayList<>();
        private float touchDownX, touchDownY;
        private boolean moved;
        private final int touchSlop = ViewConfiguration.get(MainActivity.this).getScaledTouchSlop();
        private double minX = Double.MAX_VALUE, maxX = -Double.MAX_VALUE, minY = Double.MAX_VALUE, maxY = -Double.MAX_VALUE;
        MapView() {
            super(MainActivity.this);
            for (Boundary b : boundaries) for (List<Point> ring : b.rings) for (Point p : ring) {
                minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x);
                minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y);
            }
            setContentDescription("Map of Rwanda districts. Tap a district to open its estimate profile.");
        }
        @Override protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);
            if (boundaries.isEmpty() || maxX <= minX || maxY <= minY) {
                paint.setColor(MUTED); paint.setTextSize(dp(13)); canvas.drawText("District map unavailable", dp(20), dp(40), paint); return;
            }
            rendered.clear();
            float pad = dp(10), usableW = getWidth() - 2 * pad, usableH = getHeight() - 2 * pad;
            double scale = Math.min(usableW / (maxX - minX), usableH / (maxY - minY));
            float mapW = (float) ((maxX - minX) * scale), mapH = (float) ((maxY - minY) * scale);
            float left = (getWidth() - mapW) / 2, top = (getHeight() - mapH) / 2;
            Region clip = new Region(0, 0, getWidth(), getHeight());
            double maxMetric = 0;
            for (Boundary b : boundaries) maxMetric = Math.max(maxMetric, metricValue(b.district));
            for (Boundary b : boundaries) {
                Path path = new Path();
                for (List<Point> ring : b.rings) {
                    boolean first = true;
                    for (Point p : ring) {
                        float x = (float) (left + (p.x - minX) * scale);
                        float y = (float) (top + (maxY - p.y) * scale);
                        if (first) { path.moveTo(x, y); first = false; } else path.lineTo(x, y);
                    }
                    path.close();
                }
                double value = metricValue(b.district);
                float fraction = maxMetric > 0 ? (float) (value / maxMetric) : 0;
                paint.setStyle(Paint.Style.FILL); paint.setColor(blend(Color.rgb(231, 243, 243), NAVY, fraction));
                canvas.drawPath(path, paint);
                paint.setStyle(Paint.Style.STROKE); paint.setStrokeWidth(dp(1)); paint.setColor(Color.WHITE); canvas.drawPath(path, paint);
                Region region = new Region(); region.setPath(path, clip);
                rendered.add(new RenderedBoundary(b.district, region));
            }
        }
        @Override public boolean onTouchEvent(MotionEvent event) {
            if (event.getAction() == MotionEvent.ACTION_DOWN) {
                touchDownX = event.getX();
                touchDownY = event.getY();
                moved = false;
                return true;
            }
            if (event.getAction() == MotionEvent.ACTION_MOVE) {
                if (Math.abs(event.getY() - touchDownY) > touchSlop || Math.abs(event.getX() - touchDownX) > touchSlop) {
                    moved = true;
                    // Let the containing ScrollView take over vertical swipes.
                    getParent().requestDisallowInterceptTouchEvent(false);
                }
                return true;
            }
            if (event.getAction() == MotionEvent.ACTION_UP && !moved) {
                for (int i = rendered.size() - 1; i >= 0; i--) if (rendered.get(i).region.contains((int) event.getX(), (int) event.getY())) {
                    showDistrict(rendered.get(i).district); return true;
                }
            }
            return event.getAction() != MotionEvent.ACTION_CANCEL;
        }
        private int blend(int start, int end, float t) {
            t = Math.max(0, Math.min(1, t));
            return Color.rgb((int)(Color.red(start)+(Color.red(end)-Color.red(start))*t), (int)(Color.green(start)+(Color.green(end)-Color.green(start))*t), (int)(Color.blue(start)+(Color.blue(end)-Color.blue(start))*t));
        }
    }

    private static final class District {
        String code, name, reliability;
        int samplePoor;
        double poorHouseholds, population, poorPopulation, poverty, vup, finance, exclusion, exclusionLow, exclusionHigh, excludedHouseholds;
    }
    private static final class Point { final double x, y; Point(double x, double y) { this.x = x; this.y = y; } }
    private static final class Boundary {
        final District district; final List<List<Point>> rings = new ArrayList<>();
        Boundary(District district) { this.district = district; }
        void addOuterRing(JSONArray points) throws Exception {
            List<Point> ring = new ArrayList<>();
            for (int i = 0; i < points.length(); i++) { JSONArray pair = points.getJSONArray(i); ring.add(new Point(pair.getDouble(0), pair.getDouble(1))); }
            if (!ring.isEmpty()) rings.add(ring);
        }
    }
    private static final class RenderedBoundary { final District district; final Region region; RenderedBoundary(District d, Region r) { district=d; region=r; } }
}
