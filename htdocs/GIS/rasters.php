<?php 
/*
 * Attempt to actually document the RASTERs the IEM produces and stores
 * within its archives
 */
include("../../config/settings.inc.php");
require_once "../../include/database.inc.php";
include_once "../../include/myview.php";
$t = new MyView();
$mesosite = iemdb("mesosite");

$t->title = "GIS RASTER Documentation";

$table = "";
$rs = pg_query($mesosite, "SELECT * from raster_metadata
  ORDER by name ASC");

for($i=0;$row=@pg_fetch_assoc($rs,$i);$i++){
	$table .= sprintf("<tr><th>%s</th><td>%s</td><td>%s</td></tr>\n", $row["name"],
			$row["description"], $row["units"]);

}

$t->content = <<<EOF
<h3>IEM GIS RASTER Documentation</h3>

<p>The IEM produces a number of RASTER images meant for GIS use. These RASTERs
are typically provided on the IEM website as 8 bit PNG images.  This means there
are 256 slots available for a binned value to be placed.  This page attempts to
document these RASTER images and provide the lookup table of PNG index to an 
actual value.

<p><table cellspacing="0" cellpadding="3" border="1">
<thead><tr><th>Code</th><th>Description</th><th>Units</th></tr></thead>
<tbody>
{$table}
</tbody>
</table>
EOF;
$t->render('single.phtml');
?>
