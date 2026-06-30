document.addEventListener('DOMContentLoaded', () => {
    // Add cache-busting parameter to ensure the latest data is always fetched
    const cacheBuster = '?t=' + Date.now();
    
    fetch('data.json' + cacheBuster)
        .then(res => res.json())
        .then(data => initBracket(data))
        .catch(err => console.error("Failed to load bracket data:", err));

    fetch('stats.json' + cacheBuster)
        .then(res => res.json())
        .then(stats => renderStatsTable(stats))
        .catch(err => console.error("Failed to load stats data:", err));

    document.getElementById('clear-btn').addEventListener('click', clearUI);
    
    const toggleTable = document.getElementById('toggle-table');
    const toggleBracket = document.getElementById('toggle-bracket');
    const statsWrapper = document.querySelector('.stats-wrapper');
    const bracketWrapper = document.querySelector('.bracket-wrapper');

    if (toggleTable && toggleBracket) {
        toggleTable.addEventListener('click', () => {
            toggleTable.classList.toggle('active');
            if (toggleTable.classList.contains('active')) {
                statsWrapper.style.display = 'block';
            } else {
                statsWrapper.style.display = 'none';
            }
            window.dispatchEvent(new Event('resize'));
        });

        toggleBracket.addEventListener('click', () => {
            toggleBracket.classList.toggle('active');
            if (toggleBracket.classList.contains('active')) {
                bracketWrapper.style.display = 'flex';
                setTimeout(() => window.dispatchEvent(new Event('resize')), 50);
            } else {
                bracketWrapper.style.display = 'none';
            }
        });
    }
    
    const runBtn = document.getElementById('run-btn');
    if (runBtn) {
        runBtn.addEventListener('click', () => {
            const simCount = document.getElementById('sim-count').value || 1000;
            const originalText = runBtn.textContent;
            runBtn.textContent = 'Running...';
            runBtn.disabled = true;
            
            clearUI();
            window.isSimulationActive = true;
            window.isScrambling = true;
            window.isTableScrambling = true;
            window.tableLockedRows = 0;
            window.tableLockStarted = false;
            window.initialScrambleDone = false;
            window.bracketLockStarted = false;
            startScramblingInterval();
            
            const progressWrapper = document.getElementById('progress-wrapper');
            const progressBar = document.getElementById('progress-bar');
            const progressPercentage = document.getElementById('progress-percentage');
            const progressStatus = document.getElementById('progress-status');
            
            if (progressWrapper) {
                progressWrapper.style.display = 'block';
                progressBar.style.width = '0%';
                progressPercentage.textContent = '0%';
                if (progressStatus) progressStatus.textContent = 'Starting...';
            }
            
            // Poll for progress
            const pollInterval = setInterval(() => {
                fetch('/api/progress')
                    .then(res => res.json())
                    .then(data => {
                        if (progressStatus && data.status) progressStatus.textContent = data.status;
                        
                        let pct = 0;
                        if (data.status === 'Fetching Data & ELO Ratings...') {
                            pct = 2;
                        } else if (data.status === 'Spawning Worker Processes...') {
                            pct = 5;
                        } else if (data.status === 'Aggregating Results...') {
                            pct = 99;
                        } else if (data.total > 0) {
                            // Scale remaining 5-99 space based on true progress
                            const truePct = data.progress / data.total;
                            pct = 5 + Math.floor(truePct * 94);
                        }
                        
                        if (progressBar) progressBar.style.width = `${pct}%`;
                        if (progressPercentage) progressPercentage.textContent = `${pct}%`;
                        
                        if (!window.isSimulationActive) return;
                        
                        if (data.bracket) {
                            updateBracketDOM(data.bracket);
                        }
                        
                        if (window.isScrambling && data.progress > 0) {
                            const bracketThreshold = Math.min(500, Math.max(1, data.total * 0.05));
                            if (data.progress >= bracketThreshold) {
                                if (!window.bracketLockStarted) {
                                    window.bracketLockStarted = true;
                                    const allRounds = ['roundOf32', 'roundOf16', 'quarterFinals', 'semiFinals', 'final'];
                                    
                                    window.bracketLockInterval = setInterval(() => {
                                        if (allRounds.length > 0) {
                                            const roundToLock = allRounds.shift();
                                            if (roundToLock === 'final') {
                                                const finalEl = document.querySelector('#center-final .match-card');
                                                if (finalEl) {
                                                    finalEl.querySelectorAll('.team').forEach(row => lockInRow(row));
                                                }
                                                window.isScrambling = false;
                                                if (window.scrambleInterval) {
                                                    clearInterval(window.scrambleInterval);
                                                    window.scrambleInterval = null;
                                                }
                                                document.querySelectorAll('path.connector').forEach(p => {
                                                    p.style.transition = 'opacity 0.3s ease';
                                                    p.style.opacity = '1';
                                                });
                                            } else {
                                                const cols = document.querySelectorAll(`.round-col.${roundToLock}`);
                                                cols.forEach(col => {
                                                    col.querySelectorAll('.team').forEach(row => lockInRow(row));
                                                });
                                            }
                                        } else {
                                            clearInterval(window.bracketLockInterval);
                                            window.bracketLockInterval = null;
                                        }
                                    }, 1000);
                                }
                            }
                        }
                        
                        if (window.isTableScrambling && data.progress > 0) {
                            const threshold = Math.min(250, Math.max(1, data.total * 0.05));
                            if (data.progress >= threshold && data.top10 && data.top10.length > 0) {
                                if (!window.tableLockStarted) {
                                    window.tableLockStarted = true;
                                    window.tableLockInterval = setInterval(() => {
                                        window.tableLockedRows++;
                                        if (window.tableLockedRows >= 10) {
                                            clearInterval(window.tableLockInterval);
                                            window.isTableScrambling = false;
                                            if (window.tableScrambleInterval) {
                                                clearInterval(window.tableScrambleInterval);
                                                window.tableScrambleInterval = null;
                                            }
                                        }
                                        if (window.currentStatsData) {
                                            renderStatsTable(window.currentStatsData);
                                        }
                                    }, 500);
                                }
                            }
                        }
                        
                        if (data.top10 && data.top10.length > 0) {
                            renderStatsTable(data.top10);
                        }
                    })
                    .catch(err => console.error("Error polling progress:", err));
            }, 200);
            
            fetch('/api/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ simulations: parseInt(simCount, 10) })
            })
            .then(res => {
                clearInterval(pollInterval);
                if (progressBar) progressBar.style.width = '100%';
                if (progressPercentage) progressPercentage.textContent = '100%';
                setTimeout(() => {
                    if (progressWrapper) progressWrapper.style.display = 'none';
                }, 500);
                
                if (!res.ok) throw new Error('Simulation failed on server.');
                return res.json();
            })
            .then(resData => {
                window.isSimulationActive = false;
                window.isTableScrambling = false;
                if (window.tableScrambleInterval) {
                    clearInterval(window.tableScrambleInterval);
                    window.tableScrambleInterval = null;
                }
                if (window.tableLockInterval) {
                    clearInterval(window.tableLockInterval);
                    window.tableLockInterval = null;
                }
                
                window.isScrambling = false;
                if (window.scrambleInterval) {
                    clearInterval(window.scrambleInterval);
                    window.scrambleInterval = null;
                }
                if (window.bracketLockInterval) {
                    clearInterval(window.bracketLockInterval);
                    window.bracketLockInterval = null;
                }
                
                updateBracketDOM(resData.data);
                
                document.querySelectorAll('.team.scrambling').forEach(row => {
                    lockInRow(row);
                });
                
                updateLayout(resData.data);
                
                document.querySelectorAll('path.connector').forEach(p => {
                    p.style.transition = 'opacity 0.3s ease';
                    p.style.opacity = '1';
                });
                
                renderStatsTable(resData.stats);
            })
            .catch(err => {
                console.error("Simulation error:", err);
                alert("Failed to run simulation. Is server.py running?");
                window.isSimulationActive = false;
                window.isScrambling = false;
                if (window.scrambleInterval) {
                    clearInterval(window.scrambleInterval);
                    window.scrambleInterval = null;
                }
                if (window.bracketLockInterval) {
                    clearInterval(window.bracketLockInterval);
                    window.bracketLockInterval = null;
                }
                window.isTableScrambling = false;
                if (window.tableScrambleInterval) {
                    clearInterval(window.tableScrambleInterval);
                    window.tableScrambleInterval = null;
                }
                if (window.tableLockInterval) {
                    clearInterval(window.tableLockInterval);
                    window.tableLockInterval = null;
                }
            })
            .finally(() => {
                runBtn.textContent = originalText;
                runBtn.disabled = false;
            });
        });
    }
});

function clearUI() {
    // Clear stats table
    document.getElementById('stats-body').innerHTML = '';
    
    // Clear team data but keep the empty boxes
    const teams = document.querySelectorAll('.team');
    teams.forEach(team => {
        team.classList.remove('winner', 'loser', 'highlight');
        team.dataset.teamCode = '';
        
        const flagImg = team.querySelector('.team-flag');
        if (flagImg) {
            // Hide visibility so we don't see a broken image icon or shadows,
            // but the element still takes up the exact same layout space.
            flagImg.style.visibility = 'hidden';
            flagImg.removeAttribute('src');
            flagImg.alt = '';
        }
        
        const name = team.querySelector('.team-name');
        if (name) name.innerHTML = '&nbsp;'; // &nbsp; preserves line-height
        
        const penalties = team.querySelector('.team-penalties');
        if (penalties) penalties.innerHTML = ''; // penalties can collapse without breaking main height
        
        const score = team.querySelector('.team-score');
        if (score) score.innerHTML = '&nbsp;'; // &nbsp; preserves line-height
    });
    
    // Dim the connecting lines but keep them visible
    const paths = document.querySelectorAll('.connector');
    paths.forEach(p => {
        p.classList.remove('highlight');
        p.dataset.teamCode = '';
        p.style.opacity = '0.1';
    });
    
    isStatsExpanded = false;
    const expandBtn = document.getElementById('expand-stats-btn');
    if (expandBtn) expandBtn.textContent = 'Show All Teams';
}

const roundsOrder = ['roundOf32', 'roundOf16', 'quarterFinals', 'semiFinals'];

const teamToIso = {
    "Mexico": "mx", "South Africa": "za", "South Korea": "kr", "Czechia": "cz",
    "Canada": "ca", "Bosnia and Herzegovina": "ba", "Qatar": "qa", "Switzerland": "ch",
    "Brazil": "br", "Morocco": "ma", "Haiti": "ht", "Scotland": "gb-sct",
    "United States": "us", "Australia": "au", "Paraguay": "py", "Turkey": "tr",
    "Germany": "de", "Curacao": "cw", "Ivory Coast": "ci", "Ecuador": "ec",
    "Netherlands": "nl", "Japan": "jp", "Tunisia": "tn", "Sweden": "se",
    "Belgium": "be", "Iran": "ir", "Egypt": "eg", "New Zealand": "nz",
    "Spain": "es", "Uruguay": "uy", "Saudi Arabia": "sa", "Cape Verde": "cv",
    "France": "fr", "Senegal": "sn", "Norway": "no", "Iraq": "iq",
    "Argentina": "ar", "Austria": "at", "Algeria": "dz", "Jordan": "jo",
    "Portugal": "pt", "Colombia": "co", "Uzbekistan": "uz", "DR Congo": "cd",
    "England": "gb-eng", "Croatia": "hr", "Panama": "pa", "Ghana": "gh",
    // Fallbacks for older 32-team hardcoded codes just in case
    "ARG": "ar", "SWE": "se", "MEX": "mx", "SEN": "sn", "NED": "nl", "USA": "us",
    "ENG": "gb-eng", "ECU": "ec", "BRA": "br", "JPN": "jp", "URU": "uy", "KOR": "kr",
    "ESP": "es", "MAR": "ma", "ITA": "it", "COL": "co", "FRA": "fr", "NGA": "ng",
    "GER": "de", "CAN": "ca", "POR": "pt", "IRN": "ir", "BEL": "be", "PER": "pe",
    "CRO": "hr", "AUS": "au", "SUI": "ch", "CHI": "cl", "DEN": "dk", "KSA": "sa",
    "CIV": "ci", "WAL": "gb-wls"
};

function initBracket(data) {
    // Add SVG layer for lines
    const container = document.getElementById('bracket-container');
    const svgLayer = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svgLayer.id = "bracket-lines";
    svgLayer.classList.add("svg-layer");
    container.appendChild(svgLayer);

    renderSide(data.left, 'left-half', true);
    renderSide(data.right, 'right-half', false);
    renderFinal(data.final);

    // Wait a brief moment for layout to settle, then draw lines
    setTimeout(() => {
        updateLayout(data);
        setupHoverEffects(data);
    }, 100);

    window.addEventListener('resize', () => {
        updateLayout(data);
    });
}

function updateLayout(data) {
    const wrapper = document.querySelector('.bracket-wrapper');
    const container = document.getElementById('bracket-container');
    
    // 1. Reset scale to measure accurate unscaled dimensions
    container.style.transform = 'none';
    
    // 2. Draw lines using unscaled coordinates
    drawLines(data);
    
    // 3. Calculate and apply scale
    const wrapperRect = wrapper.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();
    
    const scaleX = wrapperRect.width / containerRect.width;
    const scaleY = wrapperRect.height / containerRect.height;
    
    const scale = Math.min(scaleX, scaleY) * 0.98; // 2% margin
    
    if (scale < 1) {
        container.style.transform = `scale(${scale})`;
    }
}

function renderSide(sideData, containerId, isLeft) {
    const container = document.getElementById(containerId);
    
    roundsOrder.forEach(roundName => {
        const roundData = sideData[roundName];
        if (!roundData) return;

        const col = document.createElement('div');
        col.classList.add('round-col', roundName);
        
        const heading = document.createElement('h3');
        heading.classList.add('round-heading');
        const formattedName = roundName === 'roundOf32' ? 'Round of 32' :
                              roundName === 'roundOf16' ? 'Round of 16' :
                              roundName === 'quarterFinals' ? 'Quarterfinals' : 'Semifinals';
        heading.textContent = formattedName;
        col.appendChild(heading);
        
        roundData.forEach(match => {
            col.appendChild(createMatchCard(match));
        });
        
        container.appendChild(col);
    });
}

function renderFinal(finalData) {
    const container = document.getElementById('center-final');
    
    const wrapper = document.createElement('div');
    wrapper.style.position = 'relative';
    
    const heading = document.createElement('h3');
    heading.classList.add('round-heading');
    heading.textContent = 'Final';
    wrapper.appendChild(heading);
    
    const card = createMatchCard(finalData);
    card.classList.add('final-match-card');
    wrapper.appendChild(card);
    
    container.appendChild(wrapper);
}

function createMatchCard(match) {
    const card = document.createElement('div');
    card.classList.add('match-card');
    card.id = match.id;
    card.dataset.matchId = match.id;

    // Team 1
    card.appendChild(createTeamRow(match.team1));
    // Team 2
    card.appendChild(createTeamRow(match.team2));

    return card;
}

function createTeamRow(team) {
    const row = document.createElement('div');
    row.classList.add('team');
    
    row.dataset.realWinner = team.winner ? "true" : "false";
    row.dataset.realCode = team.code;
    row.dataset.realName = team.name;
    row.dataset.realScore = team.score;
    row.dataset.realPenalties = team.penalties !== undefined ? team.penalties : '';

    if (!window.isScrambling) {
        if (team.winner) {
            row.classList.add('winner');
        } else {
            row.classList.add('loser');
        }
    } else {
        row.classList.add('scrambling');
    }
    
    row.dataset.teamCode = team.code;

    const flagImg = document.createElement('img');
    flagImg.classList.add('team-flag');
    
    const name = document.createElement('div');
    name.classList.add('team-name');

    const penalties = document.createElement('div');
    penalties.classList.add('team-penalties');

    const score = document.createElement('div');
    score.classList.add('team-score');

    if (!window.isScrambling) {
        let baseName = team.name;
        if (baseName.includes(' (')) {
            baseName = baseName.split(' (')[0];
        }
        
        const isoCode = teamToIso[baseName] || teamToIso[team.code];
        if (isoCode) {
            flagImg.src = `https://flagcdn.com/24x18/${isoCode}.png`;
            flagImg.alt = baseName;
        } else {
            flagImg.style.backgroundColor = '#333';
        }
        
        name.textContent = team.name;

        if (team.penalties !== undefined) {
            penalties.textContent = `(${team.penalties})`;
        }

        score.textContent = team.score;
    }

    row.appendChild(flagImg);
    row.appendChild(name);
    row.appendChild(penalties);
    row.appendChild(score);

    return row;
}

function drawLines(data) {
    const svg = document.getElementById('bracket-lines');
    const container = document.getElementById('bracket-container');
    if (!svg || !container) return;
    
    svg.innerHTML = '';
    
    const containerRect = container.getBoundingClientRect();
    
    // Set viewBox so the SVG's internal coordinate system maps to the unscaled layout exactly
    svg.setAttribute('viewBox', `0 0 ${containerRect.width} ${containerRect.height}`);
    // Optional: we can remove explicit width/height since CSS sets it to 100%
    svg.removeAttribute('width');
    svg.removeAttribute('height');

    const getRectEl = (el) => {
        if (!el) return null;
        const rect = el.getBoundingClientRect();
        return {
            top: rect.top - containerRect.top,
            bottom: rect.bottom - containerRect.top,
            left: rect.left - containerRect.left,
            right: rect.right - containerRect.left,
            height: rect.height,
            width: rect.width,
            centerY: rect.top - containerRect.top + rect.height / 2
        };
    };

    const drawPath = (fromEl, toEl, isLeft, teamCode) => {
        const r1 = getRectEl(fromEl);
        const r2 = getRectEl(toEl);
        if (!r1 || !r2) return;

        let startX, startY = r1.centerY;
        let endX, endY = r2.centerY;

        if (isLeft) {
            startX = r1.right;
            endX = r2.left;
        } else {
            startX = r1.left;
            endX = r2.right;
        }

        const curveOffset = Math.abs(endX - startX) / 2;
        const d = `M ${startX} ${startY} C ${startX + (isLeft ? curveOffset : -curveOffset)} ${startY}, ${endX - (isLeft ? curveOffset : -curveOffset)} ${endY}, ${endX} ${endY}`;

        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", d);
        path.classList.add("connector");
        path.dataset.teamCode = teamCode; // Associate the edge with the specific team
        if (window.isScrambling) {
            path.style.opacity = '0';
        }
        svg.appendChild(path);
    };

    // Draw for Left Side
    drawSideLines(data.left, true, drawPath);
    // Draw for Right Side
    drawSideLines(data.right, false, drawPath);

    // Draw Final connections
    const leftSFMatch = data.left.semiFinals[0];
    const leftSFEl = document.getElementById(leftSFMatch.id);
    const fromLeft = leftSFEl.children[leftSFMatch.team1.winner ? 0 : 1];
    
    const rightSFMatch = data.right.semiFinals[0];
    const rightSFEl = document.getElementById(rightSFMatch.id);
    const fromRight = rightSFEl.children[rightSFMatch.team1.winner ? 0 : 1];

    const finalEl = document.getElementById(data.final.id);
    const toLeft = finalEl.children[0];
    const toRight = finalEl.children[1];
    
    drawPath(fromLeft, toLeft, true, fromLeft.dataset.teamCode);
    drawPath(fromRight, toRight, false, fromRight.dataset.teamCode);
}

function drawSideLines(sideData, isLeft, drawPath) {
    for (let i = 0; i < roundsOrder.length - 1; i++) {
        const currRound = sideData[roundsOrder[i]];
        const nextRound = sideData[roundsOrder[i+1]];
        if (!currRound || !nextRound) continue;

        for (let j = 0; j < nextRound.length; j++) {
            const nextMatch = nextRound[j];
            const nextMatchEl = document.getElementById(nextMatch.id);
            
            const m1 = currRound[j*2];
            const m1El = document.getElementById(m1.id);
            const m1WinnerEl = m1El.children[m1.team1.winner ? 0 : 1];
            
            const m2 = currRound[j*2+1];
            const m2El = document.getElementById(m2.id);
            const m2WinnerEl = m2El.children[m2.team1.winner ? 0 : 1];
            
            // Connect winner of m1 to top slot of nextMatch
            drawPath(m1WinnerEl, nextMatchEl.children[0], isLeft, m1WinnerEl.dataset.teamCode);
            // Connect winner of m2 to bottom slot of nextMatch
            drawPath(m2WinnerEl, nextMatchEl.children[1], isLeft, m2WinnerEl.dataset.teamCode);
        }
    }
}

// Hover functionality to highlight a specific team's path
function setupHoverEffects(data) {
    const teams = document.querySelectorAll('.team');

    teams.forEach(teamEl => {
        teamEl.addEventListener('mouseenter', (e) => {
            const teamCode = teamEl.dataset.teamCode;
            highlightTeamPath(teamCode);
        });
        
        teamEl.addEventListener('mouseleave', () => {
            clearHighlights();
        });
    });
}

function highlightTeamPath(teamCode) {
    // Highlight the specific team boxes
    const teamRows = document.querySelectorAll(`.team[data-team-code="${teamCode}"]`);
    teamRows.forEach(row => {
        row.classList.add('highlight'); 
    });
    
    // Highlight edges belonging to this team
    const paths = document.querySelectorAll('.connector');
    paths.forEach(p => {
        if (p.dataset.teamCode === teamCode) {
            p.classList.add('highlight');
            p.style.opacity = '1';
        } else {
            p.style.opacity = '0.1'; // dim other lines
        }
    });
}

function clearHighlights() {
    document.querySelectorAll('.team.highlight').forEach(el => {
        el.classList.remove('highlight');
    });
    document.querySelectorAll('.connector').forEach(el => {
        el.classList.remove('highlight');
        el.style.opacity = '1';
    });
}

let isStatsExpanded = false;
let isStatsTableListenerAttached = false;

function renderStatsTable(stats) {
    const tbody = document.getElementById('stats-body');
    const btn = document.getElementById('expand-stats-btn');
    if (!tbody || !btn) return;
    
    window.currentStatsData = stats;
    window.initialScrambleDone = true;
    
    const renderRows = () => {
        const statsData = window.currentStatsData;
        tbody.innerHTML = '';
        const limit = isStatsExpanded ? statsData.length : Math.min(10, statsData.length);
        const visibleStats = statsData.slice(0, limit);
        
        visibleStats.forEach((row, index) => {
            const tr = document.createElement('tr');
            
            if (window.isTableScrambling && index >= window.tableLockedRows) {
                tr.classList.add('table-row-scrambling');
                const tdRank = document.createElement('td');
                tdRank.classList.add('rank-col');
                tdRank.textContent = index + 1;
                tr.appendChild(tdRank);
                for(let i=0; i<7; i++) {
                    tr.appendChild(document.createElement('td'));
                }
            } else {
                const tdRank = document.createElement('td');
                tdRank.classList.add('rank-col');
                tdRank.textContent = index + 1;
                tr.appendChild(tdRank);
                
                const tdTeam = document.createElement('td');
                tdTeam.textContent = row['Team'];
                tr.appendChild(tdTeam);
                
                const keys = ['R32_%', 'R16_%', 'QF_%', 'SF_%', 'Final_%', 'Win_%'];
                keys.forEach(key => {
                    const td = document.createElement('td');
                    td.textContent = row[key] ? row[key] + '%' : '0.00%';
                    tr.appendChild(td);
                });
            }
            
            tbody.appendChild(tr);
        });
        
        if (statsData.length <= 10) {
            btn.disabled = true;
            btn.style.opacity = '0.5';
            btn.style.cursor = 'not-allowed';
            btn.textContent = 'Simulating...';
        } else {
            btn.disabled = false;
            btn.style.opacity = '1';
            btn.style.cursor = 'pointer';
            btn.textContent = isStatsExpanded ? 'Show Top 10' : 'Show All Teams';
        }
    };
    
    if (!isStatsTableListenerAttached) {
        btn.addEventListener('click', () => {
            isStatsExpanded = !isStatsExpanded;
            renderRows();
            setTimeout(() => {
                window.dispatchEvent(new Event('resize'));
            }, 50);
        });
        isStatsTableListenerAttached = true;
    }
    
    renderRows();
}

window.isScrambling = false;
window.scrambleInterval = null;

function startScramblingInterval() {
    if (window.scrambleInterval) return;
    const allIsoKeys = Object.keys(teamToIso);
    
    document.querySelectorAll('.team').forEach(row => {
        row.classList.add('scrambling');
        row.classList.remove('winner', 'loser');
        const score = row.querySelector('.team-score');
        if (score) score.textContent = '';
        const pen = row.querySelector('.team-penalties');
        if (pen) pen.textContent = '';
    });

    window.scrambleInterval = setInterval(() => {
        document.querySelectorAll('.team.scrambling').forEach(team => {
            const name = allIsoKeys[Math.floor(Math.random() * allIsoKeys.length)];
            const isoCode = teamToIso[name];
            
            const flagImg = team.querySelector('.team-flag');
            if (flagImg) {
                flagImg.src = `https://flagcdn.com/24x18/${isoCode}.png`;
                flagImg.style.visibility = 'visible';
                flagImg.style.backgroundColor = '';
            }
            
            const nameEl = team.querySelector('.team-name');
            if (nameEl) nameEl.innerHTML = name;
        });
    }, 50);

    window.tableScrambleInterval = setInterval(() => {
        if (!window.isTableScrambling) return;
        
        const scramblingRows = document.querySelectorAll('tr.table-row-scrambling');
        if (scramblingRows.length > 0) {
            scramblingRows.forEach((tr, idx) => {
                const name = allIsoKeys[Math.floor(Math.random() * allIsoKeys.length)];
                const tds = tr.querySelectorAll('td');
                if (tds.length >= 8) {
                    tds[1].textContent = name;
                    tds[2].textContent = (Math.random() * 100).toFixed(2) + '%';
                    tds[3].textContent = (Math.random() * 80).toFixed(2) + '%';
                    tds[4].textContent = (Math.random() * 60).toFixed(2) + '%';
                    tds[5].textContent = (Math.random() * 40).toFixed(2) + '%';
                    tds[6].textContent = (Math.random() * 20).toFixed(2) + '%';
                    tds[7].textContent = (Math.random() * 10).toFixed(2) + '%';
                }
            });
        } else if (!window.initialScrambleDone) {
            const tbody = document.getElementById('stats-body');
            if (!tbody) return;
            
            let html = '';
            for (let i = 0; i < 10; i++) {
                const name = allIsoKeys[Math.floor(Math.random() * allIsoKeys.length)];
                html += `<tr class="table-row-scrambling">
                    <td class="rank-col">${i + 1}</td>
                    <td>${name}</td>
                    <td>${(Math.random() * 100).toFixed(2)}%</td>
                    <td>${(Math.random() * 80).toFixed(2)}%</td>
                    <td>${(Math.random() * 60).toFixed(2)}%</td>
                    <td>${(Math.random() * 40).toFixed(2)}%</td>
                    <td>${(Math.random() * 20).toFixed(2)}%</td>
                    <td>${(Math.random() * 10).toFixed(2)}%</td>
                </tr>`;
            }
            tbody.innerHTML = html;
            const btn = document.getElementById('expand-stats-btn');
            if (btn) {
                btn.disabled = true;
                btn.style.opacity = '0.5';
                btn.style.cursor = 'not-allowed';
                btn.textContent = 'Simulating...';
            }
        }
    }, 50);
}

function lockInRow(row) {
    row.classList.remove('scrambling');
    if (row.dataset.realWinner === "true") row.classList.add('winner');
    else row.classList.add('loser');
    
    const teamName = row.dataset.realName;
    let baseName = teamName;
    if (baseName.includes(' (')) baseName = baseName.split(' (')[0];
    const isoCode = teamToIso[baseName] || teamToIso[row.dataset.realCode];
    
    const flagImg = row.querySelector('.team-flag');
    if (flagImg) {
        if (isoCode) {
            flagImg.src = `https://flagcdn.com/24x18/${isoCode}.png`;
            flagImg.alt = baseName;
            flagImg.style.backgroundColor = '';
            flagImg.style.visibility = 'visible';
        } else {
            flagImg.removeAttribute('src');
            flagImg.style.backgroundColor = '#333';
            flagImg.style.visibility = 'visible';
        }
    }
    
    const nameEl = row.querySelector('.team-name');
    if (nameEl) nameEl.textContent = teamName;
    const penEl = row.querySelector('.team-penalties');
    const pen = row.dataset.realPenalties;
    if (penEl) penEl.textContent = pen ? `(${pen})` : '';
    const scoreEl = row.querySelector('.team-score');
    if (scoreEl) scoreEl.textContent = row.dataset.realScore;
}

function updateBracketDOM(bracketData) {
    const rounds = ['roundOf32', 'roundOf16', 'quarterFinals', 'semiFinals', 'final'];
    
    rounds.forEach(round => {
        let matches = [];
        if (round === 'final') {
            if (bracketData.final) matches.push(bracketData.final);
        } else {
            if (bracketData.left && bracketData.left[round]) matches = matches.concat(bracketData.left[round]);
            if (bracketData.right && bracketData.right[round]) matches = matches.concat(bracketData.right[round]);
        }
        
        matches.forEach(match => {
            const matchEl = document.getElementById(match.id);
            if (matchEl) {
                const t1Row = matchEl.children[0];
                if (t1Row) {
                    t1Row.dataset.realWinner = match.team1.winner ? "true" : "false";
                    t1Row.dataset.realCode = match.team1.code;
                    t1Row.dataset.teamCode = match.team1.code;
                    t1Row.dataset.realName = match.team1.name;
                    t1Row.dataset.realScore = match.team1.score;
                    if (!t1Row.classList.contains('scrambling')) {
                        lockInRow(t1Row);
                    }
                }
                
                const t2Row = matchEl.children[1];
                if (t2Row) {
                    t2Row.dataset.realWinner = match.team2.winner ? "true" : "false";
                    t2Row.dataset.realCode = match.team2.code;
                    t2Row.dataset.teamCode = match.team2.code;
                    t2Row.dataset.realName = match.team2.name;
                    t2Row.dataset.realScore = match.team2.score;
                    if (!t2Row.classList.contains('scrambling')) {
                        lockInRow(t2Row);
                    }
                }
            }
        });
    });
}
