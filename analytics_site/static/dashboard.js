const reports = document.getElementById("reports");
const status = document.getElementById("status");

document.getElementById("refresh").addEventListener("click", async () => {
    const button = document.getElementById("refresh");
    button.disabled = true;
    status.textContent = "Refreshing from PostgreSQL…";

    try {
        const response = await fetch("/api/refresh", { method: "POST" });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error);
        get_reports(data);
        status.textContent = "Reports refreshed.";
    } catch (error) {
        status.textContent = error.message || "Refresh failed.";
    } finally {
        button.disabled = false;
    }
});

async function load_reports() {
    try {
        const response = await fetch("/api/reports");
        get_reports(await response.json());
        status.textContent = "";
    } catch (error) {
        status.textContent = "Could not load reports.";
    }
}

function get_reports(data) {
    reports.replaceChildren();

    for (const [title, rows] of Object.entries(data.reports)) {
        const section = document.createElement("article");
        section.className = "report";
        const heading = document.createElement("h2");
        heading.textContent = title;
        section.append(heading);

        if (rows.length === 0) {
            const empty = document.createElement("p");
            empty.className = "empty";
            empty.textContent = "No report yet. Refresh data to generate it.";
            section.append(empty);

        } else {
            const table = document.createElement("table");
            const cols = Object.keys(rows[0]).filter(function(column) {
                if (column && !column.startsWith("Unnamed")) return true;
		else return false;
           
            });

            const thead = document.createElement("thead");
            const headerRow = document.createElement("tr");
            for (const column of cols) {
                const th = document.createElement("th");
                th.textContent = column.replaceAll("_", " ");
                headerRow.append(th);
            }

            thead.append(headerRow);
            table.append(thead);

            const body = document.createElement("tbody");

            for (const row of rows) {
                const tr = document.createElement("tr");
                for (const column of cols) {
                    const td = document.createElement("td");
                    if (row[column] !== null && row[column] !== undefined) td.textContent = row[column];
                    else td.textContent = "";
                    tr.append(td);
                }
                body.append(tr);
            }
            table.append(body);
            section.append(table);
        }
        reports.append(section);
    }

    if (data.refreshed_at) document.getElementById("updated").textContent = `Last updated: ${new Date(data.refreshed_at).toLocaleString()}`;
    else document.getElementById("updated").textContent = "Not refreshed yet.";
}

load_reports();
