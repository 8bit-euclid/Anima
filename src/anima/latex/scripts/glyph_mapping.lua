module(...,package.seeall)

-- Configuration
local scale = 65536  -- 2^16sp = 1pt
local output_file = "glyph_map.json" -- Must match JSON_FILENAME

-- Node type constants
local HLIST = node.id("hlist")
local VLIST = node.id("vlist")
local GLYPH = node.id("glyph")
local GLUE = node.id("glue")
local KERN = node.id("kern")

-- Global data structure to store mappings
local glyph_data = {}
local glyph_counter = 0

-- Convert DVI coordinates (origin at bottom-left) to SVG coordinates (origin at top-left)
-- Both use points (pt) as units; flip Y axis for SVG
local function dvi_to_svg(dvi_x, dvi_y, page_height)
    return dvi_x, page_height - dvi_y
end

-- Extract font information with error handling
local function get_font_info(glyph_node)
    if not glyph_node or not glyph_node.font then
        return {
            name = "unknown",
            size = 10,
            id = 0
        }
    end
    
    local font_id = glyph_node.font
    local font_info = font.getfont(font_id)
    
    if not font_info then
        return {
            name = "unknown",
            size = 10,
            id = font_id
        }
    end
    
    return {
        name = font_info.fullname or font_info.name or "unknown",
        size = (font_info.size or 10 * scale) / scale,
        id = font_id
    }
end

-- Get actual position using LuaTeX's positioning system
local function get_current_position()
    -- Try to get position from TeX's current point
    local h_pos = 0
    local v_pos = 0
    
    -- Method 1: Try status library if available
    if status and status.get_node_position then
        local success, h, v = pcall(status.get_node_position)
        if success and h and v then
            return h / scale, v / scale
        end
    end
    
    -- Method 2: Try accessing TeX registers (may not always work)
    local success_h, current_h = pcall(function() return tex.getdimen("dimen0") end)
    local success_v, current_v = pcall(function() return tex.getdimen("dimen1") end)
    
    if success_h and success_v and current_h and current_v then
        return current_h / scale, current_v / scale
    end
    
    -- Fallback: return zeros (positions will be calculated relatively)
    return 0, 0
end

-- Process nodes recursively with proper position tracking
local function process_nodes(head, current_h, current_v, depth)
    current_h = current_h or 0
    current_v = current_v or 0
    depth = depth or 0
    
    -- Prevent infinite recursion
    if depth > 100 then
        texio.write_nl("Warning: Maximum recursion depth reached in process_nodes")
        return current_h, current_v
    end
    
    local node_ptr = head
    while node_ptr do
        if node_ptr.id == GLYPH then
            glyph_counter = glyph_counter + 1
            
            -- Get character safely
            local char_code = node_ptr.char or 0
            local utf8_char = ""
            
            -- Safe UTF-8 conversion
            if char_code > 0 then
                local success, result = pcall(utf8.char, char_code)
                if success then
                    utf8_char = result
                else
                    utf8_char = "?"
                end
            end
            
            -- Store glyph information with current position
            glyph_data[glyph_counter] = {
                char = char_code,
                unicode = string.format("U+%04X", char_code),
                utf8 = utf8_char,
                width = (node_ptr.width or 0) / scale,
                height = (node_ptr.height or 0) / scale,
                depth = (node_ptr.depth or 0) / scale,
                font = get_font_info(node_ptr),
                sequence_id = glyph_counter,
                dvi_h = current_h,
                dvi_v = current_v
            }
            
            -- Advance horizontal position by glyph width
            current_h = current_h + (node_ptr.width or 0) / scale
            
        elseif node_ptr.id == HLIST then
            -- Process horizontal list
            if node_ptr.list then
                current_h, _ = process_nodes(node_ptr.list, current_h, current_v, depth + 1)
            else
                -- Advance by the hlist width
                current_h = current_h + (node_ptr.width or 0) / scale
            end
            
        elseif node_ptr.id == VLIST then
            -- Process vertical list
            if node_ptr.list then
                _, current_v = process_nodes(node_ptr.list, current_h, current_v + (node_ptr.height or 0) / scale, depth + 1)
            else
                -- Advance vertical position
                current_v = current_v + ((node_ptr.height or 0) + (node_ptr.depth or 0)) / scale
            end
            
        elseif node_ptr.id == GLUE then
            -- Handle glue (spacing)
            current_h = current_h + (node_ptr.width or 0) / scale
            
        elseif node_ptr.id == KERN then
            -- Handle kerning
            current_h = current_h + (node_ptr.kern or 0) / scale
        end
        
        node_ptr = node_ptr.next
    end
    
    return current_h, current_v
end

-- Simple JSON serializer with proper indentation
local function serialize_json(obj, indent)
    indent = indent or 0
    local spacing = string.rep("  ", indent)
    local next_spacing = string.rep("  ", indent + 1)
    
    if type(obj) == "table" then
        -- Check if it's an array (consecutive integer keys starting from 1)
        local is_array = true
        local max_key = 0
        local key_count = 0
        
        for k, v in pairs(obj) do
            key_count = key_count + 1
            if type(k) ~= "number" or k ~= math.floor(k) or k < 1 then
                is_array = false
                break
            end
            max_key = math.max(max_key, k)
        end
        
        is_array = is_array and (key_count == max_key)
        
        local items = {}
        
        if is_array then
            for i = 1, max_key do
                if obj[i] ~= nil then
                    table.insert(items, serialize_json(obj[i], indent + 1))
                end
            end
            if #items == 0 then
                return "[]"
            end
            return "[\n" .. next_spacing .. table.concat(items, ",\n" .. next_spacing) .. "\n" .. spacing .. "]"
        else
            for k, v in pairs(obj) do
                local key_str = '"' .. tostring(k) .. '"'
                local val_str = serialize_json(v, indent + 1)
                table.insert(items, key_str .. ": " .. val_str)
            end
            if #items == 0 then
                return "{}"
            end
            return "{\n" .. next_spacing .. table.concat(items, ",\n" .. next_spacing) .. "\n" .. spacing .. "}"
        end
    elseif type(obj) == "string" then
        -- Escape special characters
        local escaped = obj:gsub("\\", "\\\\"):gsub('"', '\\"'):gsub("\n", "\\n"):gsub("\r", "\\r"):gsub("\t", "\\t")
        return '"' .. escaped .. '"'
    elseif type(obj) == "number" then
        -- Handle special numbers
        if obj ~= obj then -- NaN
            return "null"
        elseif obj == math.huge then
            return "null"
        elseif obj == -math.huge then
            return "null"
        else
            return tostring(obj)
        end
    elseif type(obj) == "boolean" then
        return tostring(obj)
    elseif obj == nil then
        return "null"
    else
        return '"' .. tostring(obj) .. '"'
    end
end

-- Safe file writing function
local function write_json_file(data, filename)
    local success, file = pcall(io.open, filename, "w")
    if not success or not file then
        texio.write_nl("Error: Cannot open file " .. filename .. " for writing")
        return false
    end
    
    local json_output = serialize_json(data)
    local write_success, write_error = pcall(function() file:write(json_output) end)
    
    file:close()
    
    if not write_success then
        texio.write_nl("Error writing to file " .. filename .. ": " .. tostring(write_error))
        return false
    end
    
    return true
end

-- Main shipout function
function shipout()
    -- Reset data
    glyph_data = {}
    glyph_counter = 0

    -- Get shipout box with error handling
    local shipout_box = tex.getbox('ShipoutBox')
    if not shipout_box then
        texio.write_nl("Warning: Shipout box is nil, terminating glyph extraction")
        return
    end
    
    -- Get initial position
    local start_h, start_v = get_current_position()
    
    -- Process all nodes with position tracking
    if shipout_box.list then
        process_nodes(shipout_box.list, start_h, start_v, 0)
    else
        texio.write_nl("Warning: Shipout box has no list, cannot process nodes")
        return
    end
    
    -- Calculate page dimensions safely
    local page_width = (shipout_box.width or 0) / scale
    local page_height = (shipout_box.height or 0) / scale
    
    -- Prepare output data
    local output_data = {
        glyphs = {},
        glyph_count = glyph_counter,
        page_dimensions = {
            width = page_width,
            height = page_height
        }
    }
    
    -- Transform coordinates and build output
    for i = 1, glyph_counter do
        local glyph = glyph_data[i]
        if glyph and glyph.dvi_h and glyph.dvi_v then
            local svg_x, svg_y = dvi_to_svg(glyph.dvi_h, glyph.dvi_v, page_height)
            
            -- Note: see 'glyph_data' for additional data that is not used in the output
            table.insert(output_data.glyphs, {
                sequence_id = glyph.sequence_id,
                character = glyph.utf8,
                position = {
                    x = svg_x, 
                    y = svg_y
                }
            })
        end
    end
    
    -- Write JSON output with error handling
    local success = write_json_file(output_data, output_file)
    if success then
        texio.write_nl("\nGlyph mapping written to " .. output_file .. " (" .. glyph_counter .. " glyphs)")
    else
        texio.write_nl("\nFailed to write glyph mapping to " .. output_file)
    end
end