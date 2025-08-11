jQuery(function($) {
        $(function() {

          'use strict';

          //-------------
          //- BAR CHART -
          //-------------

          var areaChartData = {
            labels: ["\u044f\u043d\u0432., 2025", "\u0444\u0435\u0432\u0440., 2025", "\u043c\u0430\u0440\u0442, 2025", "\u0430\u043f\u0440., 2025", "\u043c\u0430\u0439, 2025", "\u0438\u044e\u043d\u044c, 2025", "\u0438\u044e\u043b\u044c, 2025", "\u0430\u0432\u0433., 2025", "\u0441\u0435\u043d\u0442., 2025", "\u043e\u043a\u0442., 2025", "\u043d\u043e\u044f\u0431., 2025", "\u0434\u0435\u043a., 2025"],
            datasets: [{
              label: 'Задолженность',
              fillColor: 'rgba(221, 75, 57, 1)',
              strokeColor: 'rgba(221, 75, 57, 1)',
              //pointColor          : 'rgba(210, 214, 222, 1)',
              //pointStrokeColor    : '#c1c7d1',
              //pointHighlightFill  : '#fff',
              //pointHighlightStroke: 'rgba(220,220,220,1)',
              data: [0, 0, 0, 2890, 0, 0, 0, 0, 0, 0, 0, 0]
            }, {
              label: 'Погашение задолженности',
              fillColor: 'rgba(0, 166, 90, 1)',
              strokeColor: 'rgba(0, 166, 90, 1)',
              //pointColor          : '#3b8bba',
              //pointStrokeColor    : 'rgba(60,141,188,1)',
              //pointHighlightFill  : '#fff',
              //pointHighlightStroke: 'rgba(60,141,188,1)',
              data: [0, 0, 0, 4425, 0, 0, 0, 0, 0, 0, 0, 0]
            }]
          };

          var barChartCanvas = $('#barChart').get(0).getContext('2d');
          var barChart = new Chart(barChartCanvas);
          var barChartData = areaChartData;
          //        barChartData.datasets[1].fillColor   = '#00a65a';
          //        barChartData.datasets[1].strokeColor = '#00a65a';
          //        barChartData.datasets[1].pointColor  = '#00a65a';
          var barChartOptions = {
            //Boolean - Whether the scale should start at zero, or an order of magnitude down from the lowest value
            scaleBeginAtZero: true,
            //Boolean - Whether grid lines are shown across the chart
            scaleShowGridLines: true,
            //String - Colour of the grid lines
            scaleGridLineColor: 'rgba(0,0,0,.05)',
            //Number - Width of the grid lines
            scaleGridLineWidth: 1,
            //Boolean - Whether to show horizontal lines (except X axis)
            scaleShowHorizontalLines: true,
            //Boolean - Whether to show vertical lines (except Y axis)
            scaleShowVerticalLines: true,
            //Boolean - If there is a stroke on each bar
            barShowStroke: true,
            //Number - Pixel width of the bar stroke
            barStrokeWidth: 2,
            //Number - Spacing between each of the X value sets
            barValueSpacing: 5,
            //Number - Spacing between data sets within X values
            barDatasetSpacing: 1,
            //String - A legend template

            legendTemplate: '<ul class="<%=name.toLowerCase()%>-legend"><% for (var i=0; i<datasets.length ; i++){%><li><span style="background-color:<%=datasets[i].fillColor%>"></span><%if(datasets[i].label){%><%=datasets[i].label%><%}%></li><%}%></ul>',

            //Boolean - whether to make the chart responsive
            responsive: true,
            maintainAspectRatio: true
          };

          barChartOptions.datasetFill = false;
          var myBarChart = barChart.Bar(barChartData, barChartOptions);
          document.getElementById('barChart-legend').innerHTML = myBarChart.generateLegend();

          //-----------------
          //- END BAR CHART -
          //-----------------

          //-------------
          //- BAR CHART 2 -
          //-------------

          var areaChartData = {
            labels: ["\u044f\u043d\u0432., 2025", "\u0444\u0435\u0432\u0440., 2025", "\u043c\u0430\u0440\u0442, 2025", "\u0430\u043f\u0440., 2025", "\u043c\u0430\u0439, 2025", "\u0438\u044e\u043d\u044c, 2025", "\u0438\u044e\u043b\u044c, 2025", "\u0430\u0432\u0433., 2025", "\u0441\u0435\u043d\u0442., 2025", "\u043e\u043a\u0442., 2025", "\u043d\u043e\u044f\u0431., 2025", "\u0434\u0435\u043a., 2025"],
            datasets: [{
              label: 'Приход',
              fillColor: 'rgba(0, 166, 90, 1)',
              strokeColor: 'rgba(0, 166, 90, 1)',
              //pointColor          : 'rgba(210, 214, 222, 1)',
              //pointStrokeColor    : '#c1c7d1',
              //pointHighlightFill  : '#fff',
              //pointHighlightStroke: 'rgba(220,220,220,1)',
              data: [null, null, null, "18450.00", null, null, null, null, null, null, null, null]
            }, {
              label: 'Расход',
              fillColor: 'rgba(221, 75, 57, 1)',
              strokeColor: 'rgba(221, 75, 57, 1)',
              //pointColor          : '#3b8bba',
              //pointStrokeColor    : 'rgba(60,141,188,1)',
              //pointHighlightFill  : '#fff',
              //pointHighlightStroke: 'rgba(60,141,188,1)',
              data: [null, null, null, "1000.00", null, null, null, null, null, null, null, null]
            }]
          };

          var barChart2Canvas = $('#barChart2').get(0).getContext('2d');
          var barChart2 = new Chart(barChart2Canvas);
          var barChart2Data = areaChartData;
          //        barChart2Data.datasets[1].fillColor   = '#00a65a';
          //        barChart2Data.datasets[1].strokeColor = '#00a65a';
          //        barChart2Data.datasets[1].pointColor  = '#00a65a';
          var barChart2Options = {
            //Boolean - Whether the scale should start at zero, or an order of magnitude down from the lowest value
            scaleBeginAtZero: true,
            //Boolean - Whether grid lines are shown across the chart
            scaleShowGridLines: true,
            //String - Colour of the grid lines
            scaleGridLineColor: 'rgba(0,0,0,.05)',
            //Number - Width of the grid lines
            scaleGridLineWidth: 1,
            //Boolean - Whether to show horizontal lines (except X axis)
            scaleShowHorizontalLines: true,
            //Boolean - Whether to show vertical lines (except Y axis)
            scaleShowVerticalLines: true,
            //Boolean - If there is a stroke on each bar
            barShowStroke: true,
            //Number - Pixel width of the bar stroke
            barStrokeWidth: 2,
            //Number - Spacing between each of the X value sets
            barValueSpacing: 5,
            //Number - Spacing between data sets within X values
            barDatasetSpacing: 1,
            //String - A legend template

            legendTemplate: '<ul class="<%=name.toLowerCase()%>-legend"><% for (var i=0; i<datasets.length ; i++){%><li><span style="background-color:<%=datasets[i].fillColor%>"></span><%if(datasets[i].label){%><%=datasets[i].label%><%}%></li><%}%></ul>',


            //Boolean - whether to make the chart responsive
            responsive: true,
            maintainAspectRatio: true
          };

          barChart2Options.datasetFill = false;
          var myBarChart2 = barChart2.Bar(barChart2Data, barChart2Options);
          document.getElementById('barChart2-legend').innerHTML = myBarChart2.generateLegend();

          //-----------------
          //- END BAR CHART 2 -
          //-----------------
        });

      });