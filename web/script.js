        let lastUpdateTime = "Never";

        async function loadData() {
            let [rows, localModels, lastUpdate] = await eel.load_data()();
            lastUpdateTime = lastUpdate;
            updateLastUpdateLabel();
            let tableHtml = '';
            for (let [row, isInstalled] of rows) {
                let archivedClass = row[5] == 1 ? 'archived' : '';
                let installedClass = isInstalled ? 'installed' : '';
                let versions = row[6].split(', ');
                let buttons = '';
                let hasLatestInstalled = localModels.some(model => model.startsWith(`${row[1]}:`) && model.endsWith(':latest'));
                
                for (let version of versions) {
                    let isLatest = version === row[7];
                    let displayVersion = isLatest ? `${version} (latest)` : version;
                    let versionToUse = isLatest && hasLatestInstalled ? 'latest' : version;
                    
                    if (localModels.includes(`${row[1]}:${version}`) || (isLatest && hasLatestInstalled)) {
                        buttons += `<button class="uninstall-button" onclick="uninstallModel('${row[1]}', '${versionToUse}')">Uninstall ${displayVersion}</button>`;
                    } else {
                        buttons += `<button class="install-button" onclick="installModel('${row[1]}', '${version}')">Install ${displayVersion}</button>`;
                    }
                }
                
                tableHtml += `
                    <tr class="${archivedClass} ${installedClass}" style="border-bottom:1px black solid; background-color: ${isInstalled ? '#90EE90' : 'white'}">
                        <td class="model-name" valign="top" align="right"><b>${row[1]}</b></td>
                        <td>
                        ${row[2]}<br />
                        <small>
                        <b>Pulls:</b> ${row[3]}<br />
                        <b>Last Updated:</b> ${row[4]}<br />
                        <b>Project Status:</b> ${row[5] == 1 ? 'Archived' : 'Active'}<br />
                        <b>Latest Version:</b> ${row[7] || 'N/A'}
                        </small>
                        </td>
                        <td>${row[6]}</td>
                        <td>${buttons}</td>
                    </tr>
                `;
            }
            document.getElementById('modelTable').innerHTML += tableHtml;
        }

        function updateLastUpdateLabel() {
            document.getElementById('lastUpdateLabel').innerText = `Last updated at: ${lastUpdateTime}`;
        }

        async function installModel(modelName, version) {
            if (confirm(`Are you sure you want to install ${modelName}:${version}?`)) {
                let [success, message] = await eel.install_model(modelName, version)();
                document.getElementById('status').innerText = message;
                if (success) loadData();
            }
        }

        async function uninstallModel(modelName, version) {
            if (confirm(`Are you sure you want to remove this model? ${modelName}:${version}`)) {
                let [success, message] = await eel.uninstall_model(modelName, version)();
                document.getElementById('status').innerText = message;
                if (success) loadData();
            }
        }

        async function updateDatabase() {
            setStatus("Updating database...");
            let [message, newUpdateTime] = await eel.update_database()();
            setStatus(message);
            lastUpdateTime = newUpdateTime;
            updateLastUpdateLabel();
            await loadData();
        }

        function searchModel() {
            let input = document.getElementById('search').value.toLowerCase();
            let table = document.getElementById('modelTable');
            let rows = table.getElementsByTagName('tr');
            for (let i = 1; i < rows.length; i++) {
                let modelName = rows[i].getElementsByTagName('td')[0].textContent.toLowerCase();
                if (modelName.includes(input)) {
                    rows[i].style.display = '';
                    rows[i].style.backgroundColor = 'cornsilk';
                } else {
                    rows[i].style.display = 'none';
                }
            }
        }

        function clearSearch() {
            document.getElementById('search').value = '';
            let table = document.getElementById('modelTable');
            let rows = table.getElementsByTagName('tr');
            for (let i = 1; i < rows.length; i++) {
                rows[i].style.display = '';
                if (rows[i].classList.contains('installed')) {
                    rows[i].style.backgroundColor = '#90EE90';
                } else if (rows[i].classList.contains('archived')) {
                    rows[i].style.backgroundColor = '#CCCCCC';
                } else {
                    rows[i].style.backgroundColor = 'white';
                }
            }
        }

        function setStatus(message) {
            document.getElementById('statusBar').innerText = message;
        }

        eel.expose(setStatus);

document.addEventListener('DOMContentLoaded', function() {
    loadData();
});